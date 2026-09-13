# -*- coding: utf-8 -*-
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"tools\batch_verify.py"
s = open(p, encoding="utf-8").read()
old = 'ONLY = {"screenshot-20260913-142540.png"}'
new = 'ONLY = {"screenshot-20260913-142540.png", "screenshot-20260913-135242.png", "screenshot-20260913-143359.png"}'
assert old in s
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(s)
print("batch updated")
