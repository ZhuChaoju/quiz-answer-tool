# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"tools\batch_verify.py"
s = open(p, encoding="utf-8").read()
old = 'SRC_DIR = r"C:\\Users\\zcj\\Downloads\\截图\\科举"'
new = 'SRC_DIR = r"C:\\Users\\zcj\\Downloads\\截图\\科举"\nONLY = {"screenshot-20260913-142540.png"}'
assert old in s, "src pattern"
s = s.replace(old, new, 1)
old2 = '    if not fn.startswith("screenshot") or not fn.endswith(".png"):\n        continue'
new2 = '    if not fn.startswith("screenshot") or not fn.endswith(".png"):\n        continue\n    if ONLY and fn not in ONLY:\n        continue'
assert old2 in s, "filter pattern"
s = s.replace(old2, new2, 1)
ast.parse(s)
open(p, "w", encoding="utf-8").write(s)
print("batch_verify updated")
