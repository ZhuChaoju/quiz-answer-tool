# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
s = open(r"tools\test_text_modules.py", encoding="utf-8").read()
i = s.find("keju_huishi 合成")
old_seg = s[s.rfind("    # ---- 4)", 0, i):i]
print(old_seg[-600:])
p = r"tools\test_text_modules.py"
s = open(p, encoding="utf-8").read()
marker = '    r = mh.recognize(Image.open(p3).convert("RGB"), OCR_CFG)'
assert marker in s
new = """    raw_dbg = mh.roi_variants[0]["question"].crop(canvas, pad=0.02) if mh.roi_variants else mh.roi["question"].crop(canvas, pad=0.02)
    from quiz_answer_tool import ocr as _ocr

    _ls = _ocr.recognize(raw_dbg, "ch", 0.1, "tiny", False, False, 0.6)
    print("[gate调试] 题面区OCR:", [ln.text for ln in _ls])
""" + marker
s = s.replace(marker, new, 1)
ast.parse(s)
open(p, "w", encoding="utf-8").write(s)
print("debug inserted")
