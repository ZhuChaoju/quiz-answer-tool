# -*- coding: utf-8 -*-
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
for name in ("text", "icon"):
    s = open(rf"src\quiz_answer_tool\activities\{name}.py", encoding="utf-8").read()
    open(rf"D:\work\_downloads\cur_{name}.txt", "w", encoding="utf-8").write(s)
print("dumped")
