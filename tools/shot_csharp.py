# -*- coding: utf-8 -*-
"""抓取 C# 应用窗口内容（按 win32 rect 屏幕区域截屏）。"""
import ctypes
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ctypes.windll.shcore.SetProcessDpiAwareness(2)

import mss
import mss.tools

hwnd = 527984


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


rect = RECT()
ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
print("rect:", rect.left, rect.top, rect.right, rect.bottom)
with mss.mss() as sct:
    shot = sct.grab({"left": rect.left, "top": rect.top,
                     "width": rect.right - rect.left, "height": rect.bottom - rect.top})
    mss.tools.to_png(shot.rgb, shot.size, output=r"D:\work\_downloads\csharp_window.png")
print("saved")
