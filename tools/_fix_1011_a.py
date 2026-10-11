# -*- coding: utf-8 -*-
"""修复三连：变体评分/答案选项验证/OCR降采样提速。"""
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ---------- 修复1+3: text.py 变体评分 + 降采样 ----------
p = r"src\quiz_answer_tool\activities\text.py"
s = open(p, encoding="utf-8").read()

old = """        if self.roi_variants:
            # 多布局变体：逐变体 OCR 题面区，选题面文字最多的那套布局
            best_chars, best_q, best_o, best_raw = -1, None, None, ""
            for rv in self.roi_variants:
                qc = rv["question"].crop(frame, pad=0.02)
                ls_all = ocr.recognize(qc, lang, max(conf, 0.3), mt, False, dml, th)
                ls_q = [ln for ln in ls_all if not self.is_noise(ln.text)]
                chars = sum(len(ln.text) for ln in ls_q)
                if chars > best_chars:
                    best_chars, best_q, best_o, best_raw = chars, qc, rv["option"].crop(frame, pad=0.02), "".join(ln.text for ln in ls_all)
            q_crop, o_crop = best_q, best_o
            raw_all = best_raw
        else:
            q_crop = roi_q.crop(frame, pad=0.02)
            o_crop = roi_o.crop(frame, pad=0.02)
            ls_all = ocr.recognize(q_crop, lang, conf, mt, False, dml, th)
            raw_all = "".join(ln.text for ln in ls_all)"""

new = """        def _downscale(crop: Image.Image, max_w: int = 1295) -> Image.Image:
            # 大窗口(如2000x1350)直接OCR很慢：先降采样回基准宽度（文字相对大小不变）
            if crop.width > max_w:
                r = max_w / crop.width
                return crop.resize((max_w, max(1, int(crop.height * r))), Image.LANCZOS)
            return crop

        def _score_text(raw: str) -> int:
            # 变体评分：只统计"已答X题/答对X题"标题行之后的正文字符量——
            # 大窗口下变体ROI可能盖到聊天区，污染文字在标题行之前，天然被排除
            m = re.search(r"已答\\d+题[，。]?答对\\d+题[。]?|题目[:：]", raw)
            return len(raw[m.end():]) if m else 0

        if self.roi_variants:
            # 多布局变体：逐变体 OCR 题面区，按标题行后的正文字量选最优布局
            best_chars, best_q, best_o, best_raw = -1, None, None, ""
            for rv in self.roi_variants:
                qc = _downscale(rv["question"].crop(frame, pad=0.02))
                ls_all = ocr.recognize(qc, lang, max(conf, 0.3), mt, False, dml, th)
                raw = "".join(ln.text for ln in ls_all)
                sc = _score_text(raw)
                if sc > best_chars:
                    best_chars, best_q, best_o, best_raw = sc, qc, rv["option"].crop(frame, pad=0.02), raw
            q_crop, o_crop = best_q, best_o
            raw_all = best_raw
        else:
            q_crop = _downscale(roi_q.crop(frame, pad=0.02))
            o_crop = roi_o.crop(frame, pad=0.02)
            ls_all = ocr.recognize(q_crop, lang, conf, mt, False, dml, th)
            raw_all = "".join(ln.text for ln in ls_all)"""
assert old in s, "variant block not found"
s = s.replace(old, new, 1)
ast.parse(s)
open(p, "w", encoding="utf-8").write(s)
print("fix1+3 (variant scoring + downscale) ok")
