# -*- coding: utf-8 -*-
"""批量离线验证：科举文件夹的全部截图逐张跑识别管线并汇总。"""
import ast
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from PIL import Image

from quiz_answer_tool.activities import load_modules

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SRC_DIR = r"C:\Users\zcj\Downloads\截图\科举"
ONLY = {"screenshot-20260913-142540.png", "screenshot-20260913-135242.png", "screenshot-20260913-143359.png"}
OCR_CFG = {"model_type": "tiny", "lang": "ch", "confidence": 0.4, "use_dml": False}
FW, FH = 1295, 1039  # 游戏窗口标准帧

mods = {m.id: m for m in load_modules(os.path.join(ROOT, "banks"))}
keju = mods["keju"]

results = []
for fn in sorted(os.listdir(SRC_DIR)):
    if not fn.startswith("screenshot") or not fn.endswith(".png"):
        continue
    if ONLY and fn not in ONLY:
        continue
    path = os.path.join(SRC_DIR, fn)
    img = Image.open(path).convert("RGB")
    W, H = img.size
    # 游戏窗口在桌面左上角 (0,0)：原生窗口截图(1295x1039)按 1:1 裁剪；
    # 桌面大截图同样从左上角裁出游戏窗口区域
    gw = min(W, 1295)
    gh = min(H, 1039)
    if gw < 400 or gh < 300:
        print(f"{fn}: 截图尺寸异常跳过")
        continue
    frame = img.crop((0, 0, gw, gh)).resize((FW, FH), Image.LANCZOS)
    r = keju.recognize(frame, OCR_CFG)
    state_cn = {"hit": "命中", "miss_in_question": "答题中未命中", "no_dialog": "无题目"}.get(r.state, r.state)
    results.append((fn, state_cn, r.answer, r.note, r.question[:40]))
    print(f"{fn}: [{state_cn}] 答案={r.answer or '-'} | {r.note} | 题面={r.question[:36]}")

print("\n==== 汇总 ====")
from collections import Counter

cnt = Counter(x[1] for x in results)
for k, v in cnt.items():
    print(f"  {k}: {v}")
hits = [x for x in results if x[1] == "命中"]
print("\n命中列表:")
for fn, st, ans, note, q in hits:
    print(f"  {fn[:22]}: 答案={ans} ({note})")
