# -*- coding: utf-8 -*-
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import os

base = r"D:\work\quiz-answer-tool\dist\release"
for root, dirs, files in os.walk(base):
    for f in files:
        if "识别日志" in f or f.endswith(".log"):
            p = os.path.join(root, f)
            print("=== ", p, " ===")
            content = open(p, encoding="utf-8", errors="replace").read()
            tail = content[-2000:]
            print(tail)
            print()
