# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
s = open(r"tools\detect_game_now.py", encoding="utf-8").read()
# 阈值降到 160，且只找面积 ≥15000 的块（对话框题面纸面很大）
s = s.replace("mask = lum.mean(axis=2) > 175", "mask = lum.mean(axis=2) > 160")
s = s.replace("if bw * bh < 8000:", "if bw * bh < 15000:")
open(r"tools\detect_game_now.py", "w", encoding="utf-8").write(s)
print("thresholds adjusted")
