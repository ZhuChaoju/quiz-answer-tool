# -*- coding: utf-8 -*-
"""验证淡紫色占比信号：有题目框 vs 无题目框。"""
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import numpy as np
from PIL import Image

from quiz_answer_tool.activities import load_modules

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
mods = {m.id: m for m in load_modules(os.path.join(ROOT, "banks"))}

panel = np.array([200, 200, 228], dtype=np.float64)  # 选项框淡紫色的近似


def lav_frac(img, roi, pad=0.02):
    c = roi.crop(img, pad=pad)
    a = np.asarray(c.convert("RGB"), dtype=np.float64)
    return (np.abs(a - panel).sum(axis=2) < 90).mean()


# 乡试：有框（143359 原图） vs 无框（战斗帧）
qx = mods["keju_xiangshi"].rois["question"]
ox = mods["keju_xiangshi"].rois["option"]
for tag, p in (("乡试·有框", r"C:\Users\zcj\Downloads\截图\科举\screenshot-20260913-143359.png"),
               ("乡试·无框(战斗)", r"D:\work\_downloads\miss_frame.png"),
               ("乡试·无框(背包)", r"C:\Users\zcj\Downloads\截图\科举\screenshot-20260913-130908.png")):
    img = Image.open(p).convert("RGB")
    print(f"{tag}: 题面区淡紫占比={lav_frac(img, qx):.3f}  选项区淡紫占比={lav_frac(img, ox):.3f}")

# 会试：有框（春山居图帧，来自 detect_huishi_live 存的帧） vs 无框
img = Image.open(r"D:\work\_downloads\huishi_live.png").convert("RGB")
mods["keju_huishi"].rois["question"].x, mods["keju_huishi"].rois["question"].y = 49.5, 31.5
mods["keju_huishi"].rois["question"].w, mods["keju_huishi"].rois["question"].h = 30.0, 25.0
mods["keju_huishi"].rois["option"].x, mods["keju_huishi"].rois["option"].y = 49.0, 54.8
mods["keju_huishi"].rois["option"].w, mods["keju_huishi"].rois["option"].h = 31.5, 18.7
print(f"会试·有框: 题面区淡紫占比={lav_frac(img, mods['keju_huishi'].rois['question']):.3f}  "
      f"选项区={lav_frac(img, mods['keju_huishi'].rois['option']):.3f}")
