# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"src\quiz_answer_tool\activities\text.py"
s = open(p, encoding="utf-8").read()
old = "self._quadrant_locate(o_crop, answer, lang, conf, dml)"
new = "self._locate_answer_quadrant(o_crop, answer, lang, conf, dml)"
assert old in s, "call site not found"
s = s.replace(old, new, 1)
ast.parse(s)
open(p, "w", encoding="utf-8").write(s)
print("call site fixed, syntax ok")
