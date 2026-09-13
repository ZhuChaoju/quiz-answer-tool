# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
s = open(r"src\quiz_answer_tool\activities\icon.py", encoding="utf-8").read()
ast.parse(s)
print("names_with_answer:", "def names_with_answer" in s)
print("remove_name:", "def remove_name" in s)
