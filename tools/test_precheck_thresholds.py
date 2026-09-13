# -*- coding: utf-8 -*-
"""验证预检阈值：真实帧（有答题框 vs 无答题框）的区域亮度/面板色占比。"""
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import numpy as np
from PIL import Image

from quiz_answer_tool.activities import load_modules
from quiz_answer_tool import screen

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
mods = {m.id: m for m in load_modules(os.path.join(ROOT, "banks"))}

def stats(img, roi, pad=0.0):
    c = roi.crop(img, pad=pad)
    a = np.asarray(c.convert("RGB"), dtype=np.float64)
    mean_lum = a.mean()
    # 面板色占比（接近 162,168,210）
    panel = np.array([162, 168, 210], dtype=np.float64)
    frac = (np.abs(a - panel).sum(axis=2) < 75).mean()
    return mean_lum, frac

# ---- 教师节（icon 模块）：有框 vs 无框 ----
mod = mods["teachers"]
s = mod.rois["search"]
for tag, p in (("教师节·有框", r"C:\Users\zcj\Downloads\截图\screenshot-20260908-220110.png"),
               ("教师节·无框(战斗)", r"D:\work\_downloads\miss_frame.png")):
    if not os.path.exists(p):
        print(tag, "missing"); continue
    img = Image.open(p).convert("RGB")
    c = s.crop(img)
    a = np.asarray(c.convert("L"), dtype=np.float64)
    print(f"{tag}: search窗亮度均值={a.mean():.0f} (阈值带 120~195)")

# ---- 乡试（text 模块）：有框 vs 无框 ----
mod = mods["keju_xiangshi"]
q = mod.rois["question"]
for tag, p in (("乡试·有框", r"C:\Users\zcj\Downloads\截图\科举\screenshot-20260913-143359.png"),
               ("乡试·无框", r"D:\work\_downloads\miss_frame.png")):
    img = Image.open(p).convert("RGB")
    W, H = img.size
    l, t = int(W * q.x / 100), int(H * q.y / 100)
    r_, b_ = int(W * (q.x + q.w) / 100), int(H * (q.y + q.h) / 100)
    a = np.asarray(img.crop((l, t, r_, b_)).convert("L"), dtype=np.float64)
    print(f"{tag}: 题面区亮度均值={a.mean():.0f} (阈值 150)")
