# -*- coding: utf-8 -*-
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"src\quiz_answer_tool\viewer.py"
s = open(p, encoding="utf-8").read()
i = s.find('cur = (gate_main, gate_opt)')
open(r"D:\work\_downloads\view_gate2.txt", "w", encoding="utf-8").write(s[i:i + 800])
print("written")
