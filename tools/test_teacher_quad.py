# -*- coding: utf-8 -*-
"""教师节红框象限定位验证：在归档实况帧上跑识别并画红框。"""
import ast
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from PIL import Image, ImageDraw

from quiz_answer_tool.activities import load_modules

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OCR_CFG = {"model_type": "tiny", "lang": "ch", "confidence": 0.4, "use_dml": False}

frame = Image.open(r"C:\Users\zcj\Downloads\截图\screenshot-20260908-220139.png").convert("RGB")
mods = {m.id: m for m in load_modules(os.path.join(ROOT, "banks"))}
mod = mods["teachers"]
r = mod.recognize(frame, OCR_CFG)
print("答案:", r.answer or "未命中", "| state:", r.state, "| note:", r.note)
img = frame.copy()
d = ImageDraw.Draw(img)
if r.option_rect:
    d.rectangle(r.option_rect, outline=(0, 200, 0), width=3)
    print("选项区(跟随):", r.option_rect)
if r.answer_line:
    ln, sx1, sx2 = r.answer_line
    rl, rt, rr, rb = mod.rois["option"].rect_px(frame.size, 0.02)
    d.rectangle((rl + sx1 - 4, rt + ln.center_y - ln.height / 2 - 2,
                 rl + sx2 + 4, rt + ln.center_y + ln.height / 2 + 2), outline=(255, 0, 0), width=3)
    print("红框像素: x", rl + sx1, "-", rl + sx2)
crop = img.crop((150, 80, 700, 420))
crop = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
crop.save(r"D:\work\_downloads\teacher_box_check.png")
print("saved teacher_box_check.png")
