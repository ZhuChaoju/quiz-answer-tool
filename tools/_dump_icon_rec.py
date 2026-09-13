# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
s = open(r"src\quiz_answer_tool\activities\icon.py", encoding="utf-8").read()
ast.parse(s)
i = s.find("def recognize")
open(r"D:\work\_downloads\icon_rec.txt", "w", encoding="utf-8").write(s[i:i + 2400])
print("written, syntax ok")
