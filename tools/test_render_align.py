# -*- coding: utf-8 -*-
"""渲染对位验证：预览缩放后，画布上的 ROI 框必须仍对准画面里的目标。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from PIL import Image

from quiz_answer_tool.activities import load_modules
from quiz_answer_tool.viewer import Viewer

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
frame = Image.open(r"D:\work\_downloads\live_now.png").convert("RGB")
W, H = frame.size
ICON = (425, 318, 465, 358)  # 实测图标位置

modules = load_modules(os.path.join(ROOT, "banks"))
teachers = next(m for m in modules if m.id == "teachers")
app = Viewer({"interval_sec": 0.2, "ocr": {"model_type": "tiny"}, "ui": {}}, modules,
             config_path=os.path.join(ROOT, "build", "test_config.json"))
app.geometry("1400x950+40+40")
app._mod_box.current([m.id for m in modules].index("teachers"))
app._on_module_changed()
failures = []


def check(tag, box_canvas, expect_frame):
    cx = (box_canvas[0] + box_canvas[2]) / 2
    cy = (box_canvas[1] + box_canvas[3]) / 2
    fx, fy = app._to_img_coord(cx, cy)
    ex = (expect_frame[0] + expect_frame[2]) / 2
    ey = (expect_frame[1] + expect_frame[3]) / 2
    ok = abs(fx - ex) < 3 and abs(fy - ey) < 3
    print(f"{tag}: 框中心反算整帧坐标=({fx:.0f},{fy:.0f}) 期望=({ex:.0f},{ey:.0f}) {'OK' if ok else 'FAIL'}")
    if not ok:
        failures.append(tag)


def step():
    try:
        # —— 全画面模式，模拟预览线程缩放（PREVIEW_WIDTH=900 < 1036）——
        ratio = 900 / W
        thumb = frame.resize((900, int(H * ratio)), Image.BILINEAR)
        app._render(thumb, (0.0, 0.0, float(W), float(H)), (W, H))
        check("全画面 icon 框", app._canvas.coords(app._items["icon"]), ICON)
        check("全画面 option 框", app._canvas.coords(app._items["option"]),
              tuple(teachers.rois["option"].rect_px((W, H))))

        # —— 仅识别区域模式 ——
        app._roi_only.set(True)
        union = app._union_rect()
        crop = frame.crop(tuple(int(v) for v in union))
        app._render(crop, union, (W, H))
        check("仅ROI icon 框", app._canvas.coords(app._items["icon"]), ICON)
        print("render align:", "PASS" if not failures else "FAIL")
    except Exception as exc:  # noqa: BLE001
        failures.append(str(exc))
        print("render align FAILED:", exc)
    finally:
        app._on_close()


app.after(600, step)
app.mainloop()
sys.exit(1 if failures else 0)
