# -*- coding: utf-8 -*-
"""实时监测：看工具在不答题时到底在做什么（跳动原因）。"""
import ast
import io
import os
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# 检查正在运行的工具实例有没有在频繁触发 clear 和 result
p = r"src\quiz_answer_tool\viewer.py"
s = open(p, encoding="utf-8").read()

# 找到 ocr_loop 的关键流程
i = s.find("def run_recognition")
print("=== run_recognition ===")
print(s[i:i + 600])
print("\n=== gate flow ===")
j = s.find("if gate_main != last_main")
print(s[j:j + 900])
print("\n=== clear calls ===")
k = 0
for line in s.splitlines():
    k += 1
    if '"clear"' in line:
        print(f"  line {k}: {line.strip()}")
