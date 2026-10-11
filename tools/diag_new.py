# -*- coding: utf-8 -*-
"""诊断 14 点后的新截图：逐张跑识别管线，输出完整中间过程。"""
import ast
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from PIL import Image

from quiz_answer_tool.activities import load_modules
from quiz_answer_tool import ocr

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OCR_CFG = {"model_type": "tiny", "lang": "ch", "confidence": 0.4, "use_dml": False}

SRC = r"C:\Users\zcj\Downloads\截图\科举\乡试"
NEW = [fn for fn in os.listdir(SRC) if fn.startswith("ScreenShot") and fn >= "ScreenShot_2026-10-11_1329"]

mods = {m.id: m for m in load_modules(os.path.join(ROOT, "banks"))}
mod = mods["keju"]

for fn in sorted(NEW):
    path = os.path.join(SRC, fn)
    img = Image.open(path).convert("RGB")
    W, H = img.size
    print(f"\n===== {fn} ({W}x{H}) =====")

    for vi, rv in enumerate(mod.roi_variants):
        qc = rv["question"].crop(img, pad=0.02)
        ls_all = ocr.recognize(qc, "ch", max(0.4, 0.3), "tiny", False, False, mod.merge_threshold)
        raw = "".join(ln.text for ln in ls_all)
        kept = sum(len(ln.text) for ln in ls_all if not mod.is_noise(ln.text))
        print(f"  变体{vi}: kept={kept} raw={raw[:80]!r}")

    r = mod.recognize(img, OCR_CFG)
    st = {"hit": "命中", "miss_in_question": "未命中", "no_dialog": "无题目"}.get(r.state, r.state)
    print(f"  => [{st}] 答案={r.answer or '-'} | {r.note} | 题面={r.question[:44]}")

    if r.answer_line:
        ln, sx1, sx2 = r.answer_line
        rl, rt, rr, rb = mod.rois["option"].rect_px(img.size, 0.02)
        print(f"  红框: x {rl + sx1:.0f} ~ {rl + sx2:.0f}, y {rt + ln.center_y:.0f}")
