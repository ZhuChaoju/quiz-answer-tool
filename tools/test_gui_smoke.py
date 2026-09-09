# -*- coding: utf-8 -*-
"""GUI 冒烟测试：不依赖游戏，验证主窗口/模块切换/ROI锁定/浮窗/仅识别区域渲染。"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from quiz_answer_tool.activities import load_modules
from quiz_answer_tool.viewer import Viewer

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
CFG = os.path.join(ROOT, "build", "test_config.json")

import json

os.makedirs(os.path.dirname(CFG), exist_ok=True)
with open(CFG, "w", encoding="utf-8") as f:
    json.dump({"interval_sec": 0.2, "ocr": {"model_type": "tiny"}, "ui": {}}, f, ensure_ascii=False)

errors = []


def run() -> None:
    modules = load_modules(os.path.join(ROOT, "banks"))
    app = Viewer({"interval_sec": 0.2, "ocr": {"model_type": "tiny"}, "ui": {}}, modules, config_path=CFG)
    app.geometry("1200x800+50+50")

    def step1():
        try:
            ids = [m.id for m in modules]
            assert app._module.id == ids[app._mod_box.current()]
            # 模块切换到教师节（icon 模块，ROI 键不同）
            app._mod_box.current(ids.index("teachers"))
            app._on_module_changed()
            assert app._module.id == "teachers", app._module.id
            # 模块切换到元宵节（text 模块）
            app._mod_box.current(ids.index("yuanxiao"))
            app._on_module_changed()
            assert app._module.id == "yuanxiao", app._module.id
            # 锁定/解锁
            app._locked.set(False)
            app._update_roi_label()
            app._locked.set(True)
            # 浮窗
            assert app._overlay is not None and app._overlay.win.winfo_exists(), "overlay missing"
            app._overlay.update("测试题目：1+1=?", "2", "冒烟测试")
            app._overlay.move_to(300, 300)
            # 穿透切换（Windows API）
            app._clickthrough.set(True)
            app._sync_overlay()
            app._clickthrough.set(False)
            app._sync_overlay()
            # 仅识别区域模式渲染一张假帧
            from PIL import Image

            frame = Image.new("RGB", (1024, 768), (30, 40, 60))
            app._full_size = (1024, 768)
            app._render(frame, (0.0, 0.0, 1024.0, 768.0), (1024, 768))
            app._roi_only.set(True)
            union = app._union_rect()
            assert union, "union rect missing"
            crop = frame.crop(tuple(int(v) for v in union))
            app._render(crop, union, (1024, 768))
            print("gui smoke: all steps OK")
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)
            print("gui smoke FAILED:", exc)
        finally:
            app._on_close()  # 走正常关闭路径，验证 config 保存

    app.after(700, step1)
    app.mainloop()


run()
if errors:
    sys.exit(1)
print("config saved keys:", list(json.load(open(CFG, encoding="utf-8")).get("ui", {}).keys()))
