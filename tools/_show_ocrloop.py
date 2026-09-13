# -*- coding: utf-8 -*-
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
s = open(r"src\quiz_answer_tool\viewer.py", encoding="utf-8").read()
i = s.find("def ocr_loop")
print(s[i:i + 1700])
