# -*- coding: utf-8 -*-
"""抓最大化工具窗口的底部信息面板。"""
import ctypes
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ctypes.windll.shcore.SetProcessDpiAwareness(2)

import mss
import mss.tools

with mss.mss() as sct:
    mon = sct.monitors[1]
    shot = sct.grab({"left": mon["left"], "top": mon["top"] + mon["height"] - 260,
                     "width": mon["width"], "height": 260})
    mss.tools.to_png(shot.rgb, shot.size, output=r"D:\work\_downloads\tool_panel.png")
print("saved")
