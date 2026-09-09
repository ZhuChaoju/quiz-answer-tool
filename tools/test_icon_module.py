# -*- coding: utf-8 -*-
"""IconModule 端到端静态验证：直接跑 recognize()（定位+OCR+匹配+红框定位）。"""
import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from quiz_answer_tool.activities import load_modules  # noqa: E402

TRUTH = {
    "220139": "龙吟",
    "220149": "延年益寿",
    "220229": "活血",
    "220110": "冥想",
}

OCR_CFG = {"model_type": "tiny", "lang": "ch", "confidence": 0.4, "use_dml": False}

# 220139/149/229 是不同尺寸的裁剪图（对话框不在 1024x768 全画面的默认位置），
# 搜索窗按各图实际几何覆盖；真实游戏全画面用模块默认搜索窗即可。
SEARCH_OVERRIDE = {
    "220139": {"x": 32.0, "y": 20.0, "w": 14.0, "h": 20.0},
    "220149": {"x": 32.0, "y": 20.0, "w": 14.0, "h": 20.0},
    "220229": {"x": 31.0, "y": 15.0, "w": 14.0, "h": 20.0},
}

paths = sorted(
    glob.glob(r"C:\Users\zcj\Downloads\截图\screenshot-20260908-*.png")
    + glob.glob(r"C:\Users\zcj\Downloads\截图\screenshot-20260910-*.png")
)
mods = {m.id: m for m in load_modules(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "banks"))}
mod = mods["teachers"]
default_search = mod.rois["search"]
print("module:", mod.name, "rois:", {k: vars(v) for k, v in mod.rois.items()}, "icons:", len(mod.bank))

hit = 0
total = 0
for p in paths:
    tag = os.path.basename(p)[20:26]
    if "220133" in tag:  # 无校准框的对照图也跑，但不计分
        continue
    from PIL import Image

    img = Image.open(p).convert("RGB")
    if tag in SEARCH_OVERRIDE:
        from quiz_answer_tool.activities.base import Roi

        mod.rois["search"] = Roi.from_json(SEARCH_OVERRIDE[tag])
    else:
        mod.rois["search"] = default_search
    r = mod.recognize(img, OCR_CFG)
    expect = TRUTH.get(tag)
    ok = (expect is None) or (r.answer == expect)
    if expect is not None:
        total += 1
        hit += int(ok)
    print(
        f"{tag}: ans={r.answer or '-'} loc={r.answer_line is not None} box={mod.last_box} "
        f"note={r.note} {'OK' if ok else f'FAIL(expect {expect})'}"
    )
print(f"\ntruth hits: {hit}/{total}")
