# -*- coding: utf-8 -*-
"""诊断 10-11 新截图：逐张跑科举模块，输出关键词闸门/题面/答案。"""
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

for fn in sorted(os.listdir(SRC)):
    if not fn.startswith("ScreenShot"):
        continue
    img = Image.open(os.path.join(SRC, fn)).convert("RGB")
    W, H = img.size
    print(f"\n===== {fn} ({W}x{H}) =====")
    # 各变体题面区 OCR 原文
    for i, rv in enumerate(mod.roi_variants):
        qc = rv["question"].crop(img, pad=0.02)
        ls = ocr.recognize(qc, "ch", 0.3, "tiny", False, False, mod.merge_threshold)
        raw = "".join(ln.text for ln in ls)
        print(f"  变体{i} 题面OCR: {raw[:70]!r}")
    r = mod.recognize(img, OCR_CFG)
    state_cn = {"hit": "命中", "miss_in_question": "未命中", "no_dialog": "无题目"}.get(r.state, r.state)
    print(f"  => [{state_cn}] 答案={r.answer or '-'} | {r.note} | 题面={r.question[:40]}")
