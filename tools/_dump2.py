# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
s = open(r"src\quiz_answer_tool\activities\text.py", encoding="utf-8").read()
i = s.find("# ---- 识别 ----")
open(r"D:\work\_downloads\txt_rec.txt", "w", encoding="utf-8").write(s[i:i + 1000])
v = open(r"src\quiz_answer_tool\viewer.py", encoding="utf-8").read()
j = v.find("gate_main")
open(r"D:\work\_downloads\view_gate.txt", "w", encoding="utf-8").write(v[max(0, j - 600):j + 300])
print("written both")
