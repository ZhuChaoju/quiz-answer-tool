# -*- coding: utf-8 -*-
"""抓取指定句柄/标题窗口的屏幕区域。用法: python shot_window.py [标题关键词] [输出路径]"""
import ctypes
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ctypes.windll.shcore.SetProcessDpiAwareness(2)
user32 = ctypes.windll.user32

keyword = sys.argv[1] if len(sys.argv) > 1 else "答题识别工具"
out = sys.argv[2] if len(sys.argv) > 2 else r"D:\work\_downloads\window.png"


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


hwnd = user32.FindWindowW(None, keyword)
if not hwnd:
    # 退化为枚举匹配
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)
    def cb(h, _):
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(h, buf, 256)
        if keyword in buf.value:
            found.append((h, buf.value))
        return 1

    user32.EnumWindows(cb, 0)
    if not found:
        sys.exit("window not found")
    hwnd = found[0][0]

rect = RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
w, h = rect.right - rect.left, rect.bottom - rect.top
print("hwnd:", hwnd, "size:", w, h)
if w <= 0 or h <= 0:
    sys.exit("invalid rect (窗口可能已关闭)")

import mss
import mss.tools

with mss.mss() as sct:
    shot = sct.grab({"left": rect.left, "top": rect.top, "width": w, "height": h})
    mss.tools.to_png(shot.rgb, shot.size, output=out)
print("saved", out)
