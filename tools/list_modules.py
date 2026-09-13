# -*- coding: utf-8 -*-
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from quiz_answer_tool.activities import load_modules

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
mods = load_modules(os.path.join(ROOT, "banks"))
for i, m in enumerate(mods):
    print(i, "|", m.id, "|", m.name, "|", m.type, "| rois:", list(m.rois))
