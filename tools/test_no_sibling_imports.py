# -*- coding: utf-8 -*-
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import os

bad = []
for f in os.listdir(r"src\quiz_answer_tool\activities"):
    if not f.endswith(".py") or f == "__init__.py":
        continue
    p = os.path.join(r"src\quiz_answer_tool\activities", f)
    s = open(p, encoding="utf-8").read()
    for i, line in enumerate(s.splitlines(), 1):
        if ".text import" in line and f != "text.py":
            bad.append(f"{f}:{i} sibling import text: {line.strip()}")
        if ".icon import" in line and f != "icon.py":
            bad.append(f"{f}:{i} sibling import icon: {line.strip()}")
        if f == "icon.py" and ".text" in line:
            bad.append(f"{f}:{i} icon imports text: {line.strip()}")
print("sibling imports:", "NONE" if not bad else bad)
print("class IconModule count in icon.py:", open(r"src\quiz_answer_tool\activities\icon.py", encoding="utf-8").read().count("class IconModule"))
