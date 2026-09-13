# -*- coding: utf-8 -*-
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

mods = {m.id: m for m in load_modules(os.path.join(ROOT, "banks"))}
mod = mods["keju"]
print("gate_keywords:", mod.gate_keywords)
frame = Image.open(os.path.join(ROOT, "build", "test_frames", "xiangshi.png")).convert("RGB")

for i, rv in enumerate(mod.roi_variants):
    qc = rv["question"].crop(frame, pad=0.02)
    ls_q = ocr.recognize(qc, "ch", max(0.4, 0.3), "tiny", False, False, mod.merge_threshold)
    raw = "".join(ln.text for ln in ls_q)
    kept = "".join(ln.text for ln in ls_q if not mod.is_noise(ln.text))
    hit = any(k in raw for k in mod.gate_keywords)
    print(f"变体{i}: raw={raw!r}")
    print(f"        kept={kept!r} 关键词命中={hit}")
