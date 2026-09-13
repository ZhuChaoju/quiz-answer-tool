# -*- coding: utf-8 -*-
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"src\quiz_answer_tool\activities\text.py"
s = open(p, encoding="utf-8").read()

old = """        res.answer = answer
        res.matched = question_dict
        res.state = "hit" if answer else "miss_in_question"
        if answer:
            res.answer_line = find_answer_line(o_lines, answer)
            if res.answer_line is None:
                # 红框定位失败（选项文字 OCR 弱，如单个数字）：用 small 模型重识别一次
                try:
                    o_lines2 = ocr.recognize_hq(o_crop, lang, max(conf, 0.3), dml, self.merge_threshold)
                    res.lines += o_lines2
                    res.answer_line = find_answer_line(o_lines2, answer)
                except Exception:
                    pass
        else:
            res.note = "题库未命中，可录入答案"
        return res"""

new = """        res.answer = answer
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
                res.answer_line = self._quadrant_locate(o_crop, answer, lang, conf, dml)
        else:
            res.note = "题库未命中，可录入答案"
        return res

    def _quadrant_locate(self, o_crop: Image.Image, answer: str, lang: str, conf: float, dml: bool):
        \"\"\"把选项区切成 2x2 四块分别识别，返回包含答案文本的块边界（裁剪图像素坐标）。\"\"\"
        from rapidfuzz import fuzz

        w, h = o_crop.size
        quads = [
            (0, 0, w // 2, h // 2),
            (w // 2, 0, w, h // 2),
            (0, h // 2, w // 2, h),
            (w // 2, h // 2, w, h),
        ]
        want = answer.strip()
        best = None
        for (ql, qt, qr, qb) in quads:
            sub = o_crop.crop((ql, qt, qr, qb))
            sub = sub.resize((sub.width * 3, sub.height * 3), Image.LANCZOS)
            try:
                lines_q = ocr.recognize_hq(sub, lang, max(conf, 0.3), dml, self.merge_threshold)
            except Exception:
                continue
            text_q = "".join(ln.text for ln in lines_q)
            from ..matcher import normalize

            nq, nt = normalize(text_q), normalize(want)
            score = 0
            if nt and nt in nq:
                score = 100
            else:
                from rapidfuzz import fuzz

                score = int(fuzz.ratio(nt, nq)) if nt else 0
            if score >= 60 and (best is None or score > best[0]):
                best = (score, (ql, qt, qr, qb))
        if best:
            ql, qt, qr, qb = best[1]
            return (float(ql), float(qt), float(qr), float(qb))
        return None"""
assert old in s, "text.py pattern not found"
s = s.replace(old, new, 1)
import ast

ast.parse(s)
open(p, "w", encoding="utf-8").write(s)
print("quadrant fallback added, syntax ok")
