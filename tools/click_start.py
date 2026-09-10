# -*- coding: utf-8 -*-
"""向 Python 工具窗口的「开始」按钮发送后台鼠标消息（不抢焦点）。"""
import ctypes
import io
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
user32 = ctypes.windll.user32

# Python 工具主进程 PID 22956 的窗口
hwnd = user32.FindWindowW(None, "答题识别工具（仅展示，不操作游戏）")
print("hwnd:", hwnd)
assert hwnd, "window not found"


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


pt = POINT()
user32.ClientToScreen(hwnd, ctypes.byref(pt))
rect = RECT()
user32.GetClientRect(hwnd, ctypes.byref(rect))
print("client origin on screen:", pt.x, pt.y, "client size:", rect.right, rect.bottom)

# 开始按钮在窗口客户区右上：约 (client_w-130, 8)
bx = rect.right - 130
by = 8
lparam = (by << 16) | bx
user32.PostMessageW(hwnd, 0x0200, 0, lparam)      # WM_MOUSEMOVE
time.sleep(0.05)
user32.PostMessageW(hwnd, 0x0201, 1, lparam)      # WM_LBUTTONDOWN
time.sleep(0.05)
user32.PostMessageW(hwnd, 0x0202, 0, lparam)      # WM_LBUTTONUP
print("clicked at client", bx, by)
