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
        q_crop = roi_q.crop(frame, pad=0.02)
        o_crop = roi_o.crop(frame, pad=0.02)
        mt = ocr_cfg.get("model_type", "tiny")
        lang = ocr_cfg.get("lang", "ch")
        conf = float(ocr_cfg.get("confidence", 0.4))
        dml = bool(ocr_cfg.get("use_dml", False))
        # 选项区用第二引擎实例并行识别（端到端延迟 ≈ max(题目, 选项)，~200ms 量级）
        fo = _OCR_EXECUTOR.submit(ocr.recognize, o_crop, lang, conf, mt, True, dml, self.merge_threshold)
        q_lines = [
            ln for ln in ocr.recognize(q_crop, lang, conf, mt, False, dml, self.merge_threshold)
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
        else:
            res.note = "题库未命中，可录入答案"
        return res
