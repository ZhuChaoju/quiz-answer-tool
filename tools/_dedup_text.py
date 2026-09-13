# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"src\quiz_answer_tool\activities\text.py"
lines = open(p, encoding="utf-8").read().split("\n")
# 找所有文件头行
heads = [i for i, l in enumerate(lines) if "coding: utf-8" in l and i > 5]
print("header lines:", heads)
if heads:
    cut = heads[0] - 1  # 保留到第一个文件头之前
    lines = lines[:cut]
    while lines and lines[-1].strip() == "":
        lines.pop()
    open(p, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("truncated to", len(lines), "lines")
s = open(p, encoding="utf-8").read()
ast.parse(s)
print("syntax ok; headers now:", s.count("coding: utf-8"))
