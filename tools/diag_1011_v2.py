# -*- coding: utf-8 -*-
"""从工具截图裁出预览区（游戏画面），按布局变体逐张诊断。"""
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from PIL import Image

from quiz_answer_tool.activities import load_modules
from quiz_answer_tool import ocr

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SRC = r"C:\Users\zcj\Downloads\截图\科举\乡试"
OCR_CFG = {"model_type": "tiny", "lang": "ch", "confidence": 0.4, "use_dml": False}

mods = {m.id: m for m in load_modules(os.path.join(ROOT, "banks"))}
mod = mods["keju"]

# 工具窗口 2000x1350：顶部工具栏~6%，预览画布 ~6%~72%，其下信息面板
PREVIEW = (0.06, 0.065, 1.0, 0.72)

for fn in sorted(os.listdir(SRC)):
    if not fn.startswith("ScreenShot"):
        continue
    img = Image.open(os.path.join(SRC, fn)).convert("RGB")
    W, H = img.size
    l, t = int(W * PREVIEW[0]), int(H * PREVIEW[1])
    r_, b_ = int(W * PREVIEW[2]), int(H * PREVIEW[3])
    pv = img.crop((l, t, r_, b_))
    pv.save(rf"D:\work\_downloads\pv_{fn[:28]}.png")
    print(f"\n===== {fn} 预览区 {pv.size} =====")
    for i, rv in enumerate(mod.roi_variants):
        qc = rv["question"].crop(pv, pad=0.02)
        ls = ocr.recognize(qc, "ch", 0.3, "tiny", False, False, mod.merge_threshold)
        raw = "".join(ln.text for ln in ls)
        print(f"  变体{i}: {raw[:64]!r}")
    r = mod.recognize(pv, OCR_CFG)
    st = {"hit": "命中", "miss_in_question": "未命中", "no_dialog": "无题目"}.get(r.state, r.state)
    print(f"  => [{st}] 答案={r.answer or '-'} | 题面={r.question[:44]}")
