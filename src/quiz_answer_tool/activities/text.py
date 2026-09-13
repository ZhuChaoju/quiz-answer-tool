# -*- coding: utf-8 -*-
"""文字答题模块：OCR 题面 → 本地题库三级匹配 → 答案 + 选项区红框定位。

覆盖科举（乡试/会试）、元宵节灯谜等文字型活动；乡试/会试格式差异通过
各自的模块配置（关卡前缀正则、题目锚点、噪声行）表达，共用同一科举题库。
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import re
from typing import Any

from PIL import Image

from .. import ocr
from ..matcher import QuestionBank
from .base import PREFIX_RE, BaseModule, ModuleResult, Roi, find_answer_line  # noqa: F401  (re-export)

# 题目/选项并行识别用的共享执行器（进程级，两线程各绑一个 OCR 引擎实例）
_OCR_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=1)

# 关卡说明等系统文案（题面正文之外），默认噪声；模块配置可追加
DEFAULT_NOISE_RE = re.compile(
    r"离开答题|离开|当前第\s*\d|还可以答|附加考题?|附加题|第\s*\d+\s*题\s*[:：]?\s*$"
    r"|连对|科举大赛第?\s*\d*\s*关|殿试部分|[吏户礼兵刑工]部考题|已答\d+题|答对\d+题"
    r"|请指?出|看图说话|^问$|连答模式|使用法宝|^A$|^B$|^C$|^D$"
)

LEVEL_CUT_RE = re.compile(r"御前科举|第[一二三四五六七八九十百\d]+关\s*[:：]|这一关考的是|第[一二三四五六七八九十百\d]+题\s*[:：]")


class TextModule(BaseModule):
    type = "text"
    ROI_KEYS = ("question", "option")

    def __init__(self) -> None:
        self.bank: QuestionBank | None = None
        self.question_anchor = r"题目\s*[:：]"  # 题面正文锚点（截掉关卡前缀）
        self.noise_extra: re.Pattern | None = None
        self.last_question = ""  # 未命中时供答案录入用

    @classmethod
    def from_json(cls, data: dict[str, Any], bank_dir: str) -> "TextModule":
        mod = cls()
        mod._base_init(data, bank_dir)
        mod.question_anchor = data.get("question_anchor", mod.question_anchor)
        extra = data.get("noise")
        if extra:
            mod.noise_extra = re.compile("|".join(extra))
        bank_rel = data.get("bank", "questions.json")
        bank_path = os.path.join(bank_dir, bank_rel)
        try:
            mod.bank = QuestionBank.load(bank_path)
        except FileNotFoundError:
            print(f"[banks] 题库缺失: {bank_path}（模块 {mod.id} 将无法匹配，可稍后放入）")
            mod.bank = None
        mod._config_path = os.path.join(
            bank_dir, "modules", f"{mod.id}.json"
        ) if os.path.isdir(os.path.join(bank_dir, "modules")) else os.path.join(bank_dir, "module.json")
        return mod

    def config_path(self) -> str | None:
        return getattr(self, "_config_path", None)

    # ---- 题面清理 ----
    @staticmethod
    def strip_prefix(text: str, anchor: str) -> str:
        m = re.search(anchor, text)
        return text[m.end():] if m else text

    @classmethod
    def clean_question(cls, text: str, anchor: str) -> list[str]:
        """清理出题面候选。

        OCR 可能把关卡说明与题面折行乱序合并：取“题目：”锚点后的正文、
        锚点前的文本、以及按关卡词切开的首/末段，全部作为候选兜底。
        """
        stripped = cls.strip_prefix(text, anchor)
        segments = re.split(LEVEL_CUT_RE, stripped)
        cands = [stripped] + [segments[0], segments[-1]]
        if anchor and stripped != text:
            m = re.search(anchor, text)
            cands.append(text[: m.start()])  # 锚点前的文本（折行乱序时题面可能在前段）
        out: list[str] = []
        for t in cands:
            t = t.strip().strip("，。；：、,.: ")
            if len(t) >= 4 and t not in out:
                out.append(t)
        return out

    def is_noise(self, text: str) -> bool:
        t = text.strip()
        if len(t) <= 1:
            return True
        if re.search(self.question_anchor, t):
            return False
        if self.noise_extra and self.noise_extra.search(t):
            return True
        return bool(DEFAULT_NOISE_RE.search(t))

    # ---- 识别 ----
    def recognize(self, frame: Image.Image, ocr_cfg: dict[str, Any]) -> ModuleResult:
        res = ModuleResult()
        roi_q, roi_o = self.rois["question"], self.rois["option"]
        mt = ocr_cfg.get("model_type", "tiny")
        lang = ocr_cfg.get("lang", "ch")
        conf = float(ocr_cfg.get("confidence", 0.4))
        dml = bool(ocr_cfg.get("use_dml", False))
        th = self.merge_threshold
        if self.roi_variants:
            # 多布局变体：逐变体 OCR 题面区，选题面文字最多的那套布局
            best_chars, best_q, best_o = -1, None, None
            for rv in self.roi_variants:
                qc = rv["question"].crop(frame, pad=0.02)
                ls_q = [
                    ln for ln in ocr.recognize(qc, lang, max(conf, 0.3), mt, False, dml, th)
                    if not self.is_noise(ln.text)
                ]
                chars = sum(len(ln.text) for ln in ls_q)
                if chars > best_chars:
                    best_chars, best_q, best_o = chars, qc, rv["option"].crop(frame, pad=0.02)
            q_crop, o_crop = best_q, best_o
        else:
            q_crop = roi_q.crop(frame, pad=0.02)
            o_crop = roi_o.crop(frame, pad=0.02)
        # 选项区用第二引擎实例并行识别（端到端延迟 ≈ max(题目, 选项)，~200ms 量级）
        fo = _OCR_EXECUTOR.submit(ocr.recognize, o_crop, lang, conf, mt, True, dml, th)
        q_lines = [
            ln for ln in ocr.recognize(q_crop, lang, conf, mt, False, dml, th)
            if not self.is_noise(ln.text)
        ]
        # 选项区只剔除空行：科举选项常为单字（金/木/水/火），不能套用题目区的短行噪声规则
        o_lines = [ln for ln in fo.result() if ln.text.strip()]
        res.lines = q_lines + o_lines
        if not q_lines or not o_lines:
            res.state = "no_dialog"
            res.note = "识别区域内容不足"
            return res
        q_lines.sort(key=lambda ln: ln.center_y)
        anchor = self.question_anchor
        joined = "".join(ln.text for ln in q_lines)
        answer = ""
        question_dict = None
        if self.bank:
            for cand in [joined] + [ln.text for ln in q_lines]:
                for t in self.clean_question(cand, anchor):
                    question_dict = self.bank.match(t)
                    if question_dict:
                        break
                if question_dict:
                    break
        if question_dict:
            answer = str(question_dict.get("answer", ""))
            res.question = str(question_dict.get("question", joined))
        else:
            res.question = joined
            self.last_question = joined
        res.answer = answer
        res.matched = question_dict
        res.state = "hit" if answer else "miss_in_question"
        if answer:
            res.answer_line = find_answer_line(o_lines, answer)
            if res.answer_line is None:
                # 红框定位失败（选项文字 OCR 弱，如单个数字）：small 模型整块重识别
                try:
                    o_lines2 = ocr.recognize_hq(o_crop, lang, max(conf, 0.3), dml, self.merge_threshold)
                    res.lines += o_lines2
                    res.answer_line = find_answer_line(o_lines2, answer)
                except Exception:
                    pass
            if res.answer_line is None:
                # 象限兜底：2x2 四块分别放大识别，命中块的红框覆盖整块
                res.answer_line = self._locate_answer_quadrant(o_crop, answer, lang, conf, dml)
        else:
            res.note = "题库未命中，可录入答案"
        return res

    def _locate_answer_quadrant(
        self, o_crop: Image.Image, answer: str, lang: str, conf: float, dml: bool
    ):
        """红框主定位：选项区切 2x2 四块，逐块放大识别，答案文本命中的块即目标选项。

        两级识别：先 tiny（快），块间歧义或全未命中时对候选块用 small 精扫。
        返回 (伪Line, 块左x, 块右x)，红框覆盖整块（即整个选项）。
        """
        from rapidfuzz import fuzz

        from ..matcher import normalize
        from ..ocr import Line

        w, h = o_crop.size
        quads = [
            (0, 0, w // 2, h // 2),
            (w // 2, 0, w, h // 2),
            (0, h // 2, w // 2, h),
            (w // 2, h // 2, w, h),
        ]
        want = normalize(answer.strip())

        def read(q, model_type):
            ql, qt, qr, qb = q
            sub = o_crop.crop((ql, qt, qr, qb))
            sub = sub.resize((sub.width * 3, sub.height * 3), Image.LANCZOS)
            try:
                return ocr.recognize(sub, lang, max(conf, 0.3), model_type, True, dml, self.merge_threshold)
            except Exception:
                return []

        def quad_text(q, model_type):
            return normalize("".join(ln.text for ln in read(q, model_type)))

        def score_of(q, model_type):
            nt = quad_text(q, model_type)
            if not want or not nt:
                return 0
            if want in nt:
                return 100
            return int(fuzz.ratio(want, nt))

        # 第一级：tiny 快扫
        scores = [(score_of(q, "tiny"), q) for q in quads]
        scores.sort(key=lambda t: -t[0])
        best_score, best_q = scores[0]
        if best_score < 60 or (len(scores) > 1 and scores[1][0] >= best_score):
            # 歧义/全未命中：small 精扫再裁决
            scores2 = [(score_of(q, "small"), q) for q in quads]
            scores2.sort(key=lambda t: -t[0])
            if scores2[0][0] > best_score:
                best_score, best_q = scores2[0]

        if best_score < 60:
            return None
        ql, qt, qr, qb = best_q
        pseudo = Line(
            text=answer.strip(),
            center_x=(ql + qr) / 2,
            center_y=(qt + qb) / 2,
            confidence=1.0,
            width=qr - ql,
            height=qb - qt,
        )
        return pseudo, float(ql), float(qr)
