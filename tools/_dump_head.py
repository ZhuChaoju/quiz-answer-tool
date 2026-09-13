# -*- coding: utf-8 -*-
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
s = open(r"src\quiz_answer_tool\activities\text.py", encoding="utf-8").read()
i = s.find("# ---- 识别 ----")
open(r"D:\work\_downloads\txt_head.txt", "w", encoding="utf-8").write(s[i:i + 900])
print("written")
