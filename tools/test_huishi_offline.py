# -*- coding: utf-8 -*-
"""离线端到端：用归档的实况帧（会试对话框）验证 关键词闸门+象限红框。"""
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

frame = Image.open(r"D:\work\_downloads\huishi_live.png").convert("RGB")
mods = {m.id: m for m in load_modules(os.path.join(ROOT, "banks"))}
mod = mods["keju_huishi"]
r = mod.recognize(frame, OCR_CFG)
print("state:", r.state, "| 答案:", r.answer or "未命中", "| note:", r.note)
print("题面:", r.question[:60])
if r.answer_line:
    ln, sx1, sx2 = r.answer_line
    rl, rt, rr, rb = mod.rois["option"].rect_px(frame.size, 0.02)
    print(f"红框像素: x {rl + sx1:.0f} ~ {rl + sx2:.0f}, y中心 {rt + ln.center_y:.0f}")
    img = frame.copy()
    d = ImageDraw.Draw(img)
    d.rectangle((rl + sx1 - 4, rt + ln.center_y - ln.height / 2 - 2,
                 rl + sx2 + 4, rt + ln.center_y + ln.height / 2 + 2), outline=(255, 0, 0), width=3)
    crop = img.crop((450, 500, 1100, 780))
    crop.save(r"D:\work\_downloads\huishi_box_check.png")
    print("saved huishi_box_check.png")
