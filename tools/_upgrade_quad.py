# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"src\quiz_answer_tool\activities\text.py"
s = open(p, encoding="utf-8").read()

# 1) 主流程改为：象限定位优先（框=整个选项区域），失败再走原有整块 HQ 兜底
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
            # 红框主路径：2x2 象限识别（每块独立放大识别，框=整个选项区域）
            res.answer_line = self._locate_answer_quadrant(o_crop, answer, lang, conf, dml)
            if res.answer_line is None:
                # 象限未命中：small 模型整块重识别 + 行级定位兜底
                try:
                    o_lines2 = ocr.recognize_hq(o_crop, lang, max(conf, 0.3), dml, self.merge_threshold)
                    res.lines += o_lines2
                    res.answer_line = find_answer_line(o_lines2, answer)
                except Exception:
                    pass
        else:
            res.note = "题库未命中，可录入答案"
        return res"""
rep_ok = old in s
print("main flow replace:", rep_ok)
s = s.replace(old, new, 1)

# 2) _quadrant_locate 升级为两级（tiny 快扫 → small 精扫）
i = s.find("    def _quadrant_locate")
j = s.find("\n\n", s.find("return None", i))
old_quad = s[i:j]
new_quad = """    def _locate_answer_quadrant(
        self, o_crop: Image.Image, answer: str, lang: str, conf: float, dml: bool
    ):
        \"\"\"红框主定位：选项区切 2x2 四块，逐块放大识别，答案文本命中的块即目标选项。

        两级识别：先 tiny（快），块间歧义或全未命中时对候选块用 small 精扫。
        返回 (伪Line, 块左x, 块右x)，红框覆盖整块（即整个选项）。
        \"\"\"
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

"""
s = s[:i] + new_quad + s[j + 1:]
ast.parse(s)
open(p, "w", encoding="utf-8").write(s)
print("quadrant locator upgraded, syntax ok")
