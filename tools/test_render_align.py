# -*- coding: utf-8 -*-
"""渲染对位验证：预览缩放后，画布上的 ROI 框必须仍对准画面里的目标。

独立复算框的期望画布坐标（不经 _to_display），并检查显示图片的实际像素
尺寸 == 目标尺寸（create_image 不会缩放图片，尺寸不符即错位）。
"""

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


def expected_canvas(rect, box):
    """独立复算：框在画布上的期望坐标（不调用 _to_display）。"""
    cw = app._canvas.winfo_width()
    ch = app._canvas.winfo_height()
    rw = rect[2] - rect[0]
    rh = rect[3] - rect[1]
    scale = min(cw / rw, ch / rh)
    disp_w, disp_h = int(rw * scale), int(rh * scale)
    ox, oy = cw // 2 - disp_w // 2, ch // 2 - disp_h // 2
    x1 = ox + (box[0] - rect[0]) * scale
    y1 = oy + (box[1] - rect[1]) * scale
    x2 = ox + (box[2] - rect[0]) * scale
    y2 = oy + (box[3] - rect[1]) * scale
    return (x1, y1, x2, y2), (disp_w, disp_h)


def check(tag, box_canvas, expect_canvas):
    diffs = [abs(a - b) for a, b in zip(box_canvas, expect_canvas)]
    ok = all(d < 1.5 for d in diffs)
    print(f"{tag}: drawn={[round(v, 1) for v in box_canvas]} expect={[round(v, 1) for v in expect_canvas]}"
          f" diffs={[round(d, 1) for d in diffs]} {'OK' if ok else 'FAIL'}")
    if not ok:
        failures.append(tag)


def step():
    try:
        # 等窗口布局完全稳定（画布尺寸不再变化）再渲染与测量
        last = None
        for _ in range(60):
            app.update_idletasks()
            app.update()
            cur = (app._canvas.winfo_width(), app._canvas.winfo_height())
            if cur == last and cur[0] > 200:
                break
            last = cur
        print(f"canvas settled: {app._canvas.winfo_width()}x{app._canvas.winfo_height()}")

        # —— 全画面模式 ——
        app._render(frame, (0.0, 0.0, float(W), float(H)), (W, H))
        icon_rect = teachers.rois["icon"].rect_px((W, H))
        exp, disp = expected_canvas((0.0, 0.0, float(W), float(H)), icon_rect)
        check("全画面 icon 框位置", app._canvas.coords(app._items["icon"]), exp)
        if app._photo.width() != disp[0] or app._photo.height() != disp[1]:
            failures.append("全画面 图片尺寸")
            print(f"全画面 图片尺寸 FAIL: photo={app._photo.width()}x{app._photo.height()} expect={disp}")
        else:
            print(f"全画面 图片尺寸 OK: {disp}")

        # —— 仅识别区域模式 ——
        app._roi_only.set(True)
        union = app._union_rect()
        crop = frame.crop(tuple(int(v) for v in union))
        app._render(crop, union, (W, H))
        exp, disp = expected_canvas(union, icon_rect)
        check("仅ROI icon 框位置", app._canvas.coords(app._items["icon"]), exp)
        if app._photo.width() != disp[0] or app._photo.height() != disp[1]:
            failures.append("仅ROI 图片尺寸")
            print(f"仅ROI 图片尺寸 FAIL: photo={app._photo.width()}x{app._photo.height()} expect={disp}")
        else:
            print(f"仅ROI 图片尺寸 OK: {disp}")
        print("render align:", "PASS" if not failures else "FAIL")
    except Exception as exc:  # noqa: BLE001
        failures.append(str(exc))
        print("render align FAILED:", exc)
    finally:
        app._on_close()


app.after(600, step)
app.mainloop()
sys.exit(1 if failures else 0)
