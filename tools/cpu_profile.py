# -*- coding: utf-8 -*-
"""CPU 分析：识别流程各步骤计时。"""
import ast
import io
import os
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from PIL import Image

from quiz_answer_tool.activities import load_modules
from quiz_answer_tool import ocr, screen

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OCR_CFG = {"model_type": "tiny", "lang": "ch", "confidence": 0.4, "use_dml": False}

sources = [x for x in screen.list_sources() if x.kind == "window" and "ONLINE" in x.name.upper()]
frame, _ = screen.capture(sources[0])
img = frame.convert("RGB")

mods = {m.id: m for m in load_modules(os.path.join(ROOT, "banks"))}
mod = mods["keju"]
q_crop = mod.roi_variants[0]["question"].crop(img, pad=0.02)
o_crop = mod.roi_variants[0]["option"].crop(img, pad=0.02)

# 1) 题面 OCR
t0 = time.perf_counter()
q_lines = ocr.recognize(q_crop, "ch", 0.4, "tiny", False, False, 0.6)
t1 = time.perf_counter()
print(f"题面 OCR (tiny): {(t1 - t0) * 1000:.0f}ms")

# 2) 选项 OCR
t0 = time.perf_counter()
o_lines = ocr.recognize(o_crop, "ch", 0.4, "tiny", True, False, 0.6)
t1 = time.perf_counter()
print(f"选项 OCR (tiny): {(t1 - t0) * 1000:.0f}ms")

# 3) 象限识别 (4块 × tiny 3x放大)
w, h = o_crop.size
quads = [(0, 0, w // 2, h // 2), (w // 2, 0, w, h // 2), (0, h // 2, w // 2, h), (w // 2, h // 2, w, h)]
t0 = time.perf_counter()
for ql, qt, qr, qb in quads:
    sub = o_crop.crop((ql, qt, qr, qb))
    sub = sub.resize((sub.width * 3, sub.height * 3), Image.LANCZOS)
    ocr.recognize(sub, "ch", 0.3, "tiny", True, False, 0.6)
t1 = time.perf_counter()
print(f"象限 tiny×4: {(t1 - t0) * 1000:.0f}ms")

# 4) 象限 small
t0 = time.perf_counter()
for ql, qt, qr, qb in quads:
    sub = o_crop.crop((ql, qt, qr, qb))
    sub = sub.resize((sub.width * 3, sub.height * 3), Image.LANCZOS)
    ocr.recognize(sub, "ch", 0.3, "small", True, False, 0.6)
t1 = time.perf_counter()
print(f"象限 small×4: {(t1 - t0) * 1000:.0f}ms")

# 5) 全流程
t0 = time.perf_counter()
r = mod.recognize(img, OCR_CFG)
t1 = time.perf_counter()
print(f"全流程 recognize: {(t1 - t0) * 1000:.0f}ms")

# 6) 每秒可跑多少次
print(f"\n结论: 全流程 {1000 / max((t1 - t0) * 1000, 1):.1f} 次/秒 → CPU 占用 ≈ {(t1 - t0) * 1000 / 330 * 100:.0f}%")
