# -*- coding: utf-8 -*-
"""实况循环冒烟：对真实屏幕跑 preview+ocr 双线程 6 秒，验证截图/识别/队列不崩。"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from quiz_answer_tool.activities import load_modules
from quiz_answer_tool import screen
from quiz_answer_tool.viewer import Viewer

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

modules = load_modules(os.path.join(ROOT, "banks"))
_t0 = None
app = Viewer({"interval_sec": 0.05, "ocr": {"model_type": "tiny"}, "ui": {}}, modules,
             config_path=os.path.join(ROOT, "build", "test_config.json"))


def step1():
    global _t0
    import os as _os

    _t0 = _os.times()
    app._reload_sources()
    src = next((s for s in app._sources if s.kind == "monitor"), None)
    assert src is not None, "no monitor source"
    app._roi_only.set(True)
    app._start_threads(src)
    print("threads started, running 6s ...")


def step2():
    import os as _os

    t1 = _os.times()
    try:
        while True:
            app._result_queue.get_nowait()
    except Exception:
        pass
    app._running = False
    app._generation += 1
    cpu = (t1.user - _t0.user) + (t1.system - _t0.system)
    print(f"loop CPU over ~6s: {cpu:.2f}s -> avg {cpu / 6.0:.3f} cores")
    print("live loop OK (no crashes); results depend on screen content")
    app._on_close()


app.after(300, step1)
app.after(6300, step2)
app.mainloop()
print("done")
