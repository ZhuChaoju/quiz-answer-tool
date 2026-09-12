# -*- coding: utf-8 -*-
"""等工具窗口出现 → 最大化 → 点开始 → 确认循环运行。"""
import ctypes
import io
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
user32 = ctypes.windll.user32

title = "答题识别工具（仅展示，不操作游戏）"
hwnd = 0
deadline = time.time() + 120
while time.time() < deadline:
    hwnd = user32.FindWindowW(None, title)
    if hwnd:
        break
    time.sleep(1)
print("hwnd:", hwnd)
if not hwnd:
    sys.exit("window never appeared")

time.sleep(1.5)
user32.ShowWindow(hwnd, 3)  # 最大化
time.sleep(1.0)


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


rect = RECT()
user32.GetClientRect(hwnd, ctypes.byref(rect))
bx = rect.right - 130
by = 8
lparam = (by << 16) | bx
user32.PostMessageW(hwnd, 0x0200, 0, lparam)
time.sleep(0.05)
user32.PostMessageW(hwnd, 0x0201, 1, lparam)
time.sleep(0.05)
user32.PostMessageW(hwnd, 0x0202, 0, lparam)
print(f"clicked Start at client ({bx},{by})")
time.sleep(6)

# 抓浮窗确认识别循环在跑
import mss
import mss.tools

ov = user32.FindWindowW(None, "答题浮窗")
if ov:
    r2 = RECT()
    user32.GetWindowRect(ov, ctypes.byref(r2))
    with mss.mss() as sct:
        shot = sct.grab({"left": r2.left, "top": r2.top,
                         "width": r2.right - r2.left, "height": r2.bottom - r2.top})
        mss.tools.to_png(shot.rgb, shot.size, output=r"D:\work\_downloads\ov_now.png")
    print("overlay captured")
else:
    print("overlay not found yet")
