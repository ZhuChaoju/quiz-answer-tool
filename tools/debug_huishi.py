# -*- coding: utf-8 -*-
"""调试会试居中样本：OCR 行、清理候选、匹配过程。"""
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from PIL import Image

from quiz_answer_tool.activities import load_modules
from quiz_answer_tool.activities.text import TextModule
from quiz_answer_tool import ocr

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OCR_CFG = {"model_type": "tiny", "lang": "ch", "confidence": 0.4, "use_dml": False}

mods = {m.id: m for m in load_modules(os.path.join(ROOT, "banks"))}
mod = mods["keju_huishi"]

web = Image.open(r"D:\work\_downloads\keju_huishi_web.jpg").convert("RGB")
dlg = web.crop((420, 25, 1290, 830))
live = Image.new("RGB", (1036, 831), (60, 70, 90))
live.paste(dlg, ((1036 - dlg.width) // 2, (831 - dlg.height) // 2))

q_crop = mod.rois["question"].crop(live, pad=0.02)
q_crop.save(r"D:\work\_downloads\huishi_qcrop.png")
print("q_crop size:", q_crop.size)
q_lines = ocr.recognize(q_crop, "ch", 0.4, "tiny", False, False)
for ln in q_lines:
    print(f"  line y={ln.center_y:.0f} x={ln.center_x:.0f} h={ln.height:.0f}: {ln.text!r}")

q_lines_f = [ln for ln in q_lines if not mod.is_noise(ln.text)]
q_lines_f.sort(key=lambda ln: ln.center_y)
joined = "".join(ln.text for ln in q_lines_f)
print("joined:", joined)
for cand in TextModule.clean_question(joined, mod.question_anchor):
    print("cand:", cand, "->", mod.bank.match(cand) is not None)
