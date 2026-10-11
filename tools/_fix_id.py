# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"tools\scrape_bank.py"
s = open(p, encoding="utf-8").read()
old = 'next_id = max(e.get("id", 0) for e in existing) + 1'
new = 'next_id = max(int(e.get("id", 0)) for e in existing) + 1'
assert old in s
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(s)
print("id type fixed")
