# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"tools\_dump_q.py"
s = open(p, encoding="utf-8").read()
s = s.replace('mod.roi["question"]', 'mod.rois["question"]')
open(p, "w", encoding="utf-8").write(s)
print("fixed")
