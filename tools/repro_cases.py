# -*- coding: utf-8 -*-
"""复现用户截图里的两道乡试题：OCR + 题库匹配全流程诊断。"""
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
mod = mods["keju_xiangshi"]

# 两张用户截图：游戏窗口在其画面中的位置（从截图目测的对话框区域）
CASES = [
    ("case1-好友度", r"C:\Users\zcj\.zcode\cli\image-cache\sess_6499c656-d698-4726-8577-3ffe6005d047\image-92e4eccc56c814733566f36c5c692c46.png",
     (390, 350, 1190, 980)),
    ("case2-天王令", r"C:\Users\zcj\.zcode\cli\image-cache\sess_6499c656-d698-4726-8577-3ffe6005d047\image-b74cd6becb883f53a11e9e99e64ac19f.png",
     (1450, 580, 2350, 1290)),
]

for tag, path, dlg in CASES:
    img = Image.open(path).convert("RGB")
    W, H = img.size
    print(f"\n===== {tag} (image {W}x{H}) =====")
    # 把对话框区域映射到整个画面的百分比坐标（乡试 ROI 是百分比的）
    # 对话框占画面：按截图目测的框
    dl, dt, dr, db = dlg
    frame = img  # 直接用整图 + 平移 ROI：乡试 ROI 按窗口百分比定义，
    # 这里把对话框居中虚拟成一张“窗口帧”，让模块 ROI 落在对话框内容上
    fw, fh = 1295, 1039  # 标准窗口帧
    # 从截图裁出对话框内容，贴到 1295x1039 的居中位置
    content = img.crop((dl, dt, dr, db))
    scale = min((fw * 0.87) / content.width, (fh * 0.75) / content.height)
    content = content.resize((int(content.width * scale), int(content.height * scale)), Image.LANCZOS)
    canvas = Image.new("RGB", (fw, fh), (40, 50, 60))
    canvas.paste(content, ((fw - content.width) // 2, (fh - content.height) // 2))
    canvas.save(rf"D:\work\_downloads\repro_{tag}.png")

    r = mod.recognize(canvas, OCR_CFG)
    print("匹配题库题面:", (r.matched or {}).get("question", "无"))
    print("答案:", r.answer or "未命中", "| state:", r.state, "| note:", r.note)
    print("识别行:")
    for ln in r.lines:
        print(f"   {ln.text!r}")
