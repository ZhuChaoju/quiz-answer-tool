# -*- coding: utf-8 -*-
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from PIL import Image

from quiz_answer_tool.activities import load_modules
from quiz_answer_tool import ocr

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
mods = {m.id: m for m in load_modules(os.path.join(ROOT, "banks"))}
mod = mods["keju"]
frame = Image.open(r"C:\Users\zcj\Downloads\截图\科举\screenshot-20260913-142540.png").convert("RGB")
q_crop = mod.rois["question"].crop(frame, pad=0.02)
q_crop.save(r"D:\work\_downloads\qcrop_142540.png")
ls = ocr.recognize(q_crop, "ch", 0.3, "tiny", False, False, mod.merge_threshold)
print("题面区 OCR:")
for ln in ls:
    print("  ", ln.text)
