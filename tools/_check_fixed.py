# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
s = open(r"src\quiz_answer_tool\activities\text.py", encoding="utf-8").read()
ast.parse(s)
print("calls old _quadrant_locate:", "_quadrant_locate(" in s)
print("has new def:", "def _locate_answer_quadrant" in s)
print("calls new:", "self._locate_answer_quadrant(" in s)
