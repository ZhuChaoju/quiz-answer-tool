# -*- coding: utf-8 -*-
"""最大化工具窗口 → 后台点击「开始」。"""
import ctypes
import io
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
user32 = ctypes.windll.user32

hwnd = user32.FindWindowW(None, "答题识别工具（仅展示，不操作游戏）")
print("hwnd:", hwnd)
if not hwnd:
    sys.exit("not found")

user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
time.sleep(0.8)


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


rect = RECT()
user32.GetClientRect(hwnd, ctypes.byref(rect))
print("client:", rect.right, rect.bottom)
bx = rect.right - 130
by = 8
lparam = (by << 16) | bx
user32.PostMessageW(hwnd, 0x0200, 0, lparam)
time.sleep(0.05)
user32.PostMessageW(hwnd, 0x0201, 1, lparam)
time.sleep(0.05)
user32.PostMessageW(hwnd, 0x0202, 0, lparam)
print(f"clicked Start at client ({bx},{by})")
