# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"src\quiz_answer_tool\activities\text.py"
s = open(p, encoding="utf-8").read()
ast.parse(s)
i = s.find("未检测到题目关键词")
print("keyword gate at char:", i)
if i > 0:
    j = s.rfind("\n", 0, i - 200)
    print(s[i - 400: i + 200])
print("total lines:", len(s.splitlines()))
