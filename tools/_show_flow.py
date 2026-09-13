# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"src\quiz_answer_tool\activities\text.py"
s = open(p, encoding="utf-8").read()
ast.parse(s)
print("syntax ok")
i = s.find("res.answer = answer")
print(s[i: i + 900])
