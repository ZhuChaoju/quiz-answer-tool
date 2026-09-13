# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"tools\audit_icons.py"
s = open(p, encoding="utf-8").read()
old = 'ICON_DIR = os.path.join(ROOT, "banks", "teachers", "icons")\nentries = json.load(open(os.path.join(ROOT, "banks", "teachers", "icons.json"), encoding="utf-8-sig"))'
new = ('ICON_DIR = os.path.join(ROOT, "banks", "teachers", "icons")\n'
       'entries = json.load(open(os.path.join(ROOT, "dist", "release", "banks", "teachers", "icons.json"), encoding="utf-8-sig"))')
assert old in s
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(s)
print("audit reads release copy now")
