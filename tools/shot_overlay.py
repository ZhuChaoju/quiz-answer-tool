# -*- coding: utf-8 -*-
"""抓答题浮窗内容。用法: python shot_overlay.py [输出路径]"""
import ctypes
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
user32 = ctypes.windll.user32
ctypes.windll.shcore.SetProcessDpiAwareness(2)

out = sys.argv[1] if len(sys.argv) > 1 else r"D:\work\_downloads\overlay.png"
hwnd = user32.FindWindowW(None, "答题浮窗")
print("overlay hwnd:", hwnd)
if not hwnd:
    sys.exit("overlay not found")


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


rect = RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
print("rect:", rect.left, rect.top, rect.right, rect.bottom)

import mss
import mss.tools

with mss.mss() as sct:
    shot = sct.grab({"left": rect.left, "top": rect.top,
                     "width": rect.right - rect.left, "height": rect.bottom - rect.top})
    mss.tools.to_png(shot.rgb, shot.size, output=out)
print("saved", out)
