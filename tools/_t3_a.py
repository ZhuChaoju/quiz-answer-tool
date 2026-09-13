# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ---- 需求3-1: QuestionBank 支持按答案查找 ----
p = r"src\quiz_answer_tool\matcher.py"
s = open(p, encoding="utf-8").read()
old = """    def add(self, question: str, answer: str) -> None:
        \"\"\"运行时收录一条题目答案（题目已存在时用新答案覆盖旧答案）。\"\"\""""
new = """    def find_by_answer(self, answer: str) -> list[dict]:
        \"\"\"按答案文本查条目（归一化精确匹配），供录入查重与删除。\"\"\""""
assert old in s, "add method not found"
print("found")
