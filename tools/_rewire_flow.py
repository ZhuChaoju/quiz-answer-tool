# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"src\quiz_answer_tool\activities\text.py"
s = open(p, encoding="utf-8").read()

old = """        if answer:
            res.answer_line = find_answer_line(o_lines, answer)
            if res.answer_line is None:
                # 红框定位失败（选项文字 OCR 弱，如单个数字）：用 small 模型重识别一次
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
        return res"""
new = """        if answer:
            # 红框主路径：2x2 象限识别（每块独立放大识别，红框=整个选项区域）
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
assert old in s, "flow pattern not found"
s = s.replace(old, new, 1)
ast.parse(s)
open(p, "w", encoding="utf-8").write(s)
print("flow rewired, syntax ok")
