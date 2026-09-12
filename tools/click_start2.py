# -*- coding: utf-8 -*-
"""精确点击工具窗口的「开始」按钮（按实际客户区尺寸计算）。"""
import ctypes
import io
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
user32 = ctypes.windll.user32

hwnd = user32.FindWindowW(None, "答题识别工具（仅展示，不操作游戏）")
print("hwnd:", hwnd)
if not hwnd:
    sys.exit("window not found")


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


rect = RECT()
user32.GetClientRect(hwnd, ctypes.byref(rect))
w = rect.right
print("client:", w, rect.bottom)

# 工具布局：右上角按钮序为 [开始] 最右；「保存为预设」「锁定识别区域」在其左侧
# 「开始」按钮中心约在 client_w - 118, y = 14
bx = w - 118
by = 14
lparam = (by << 16) | bx
for msg in (0x0200, 0x0201, 0x0202):
    user32.PostMessageW(hwnd, msg, 1 if msg == 0x0201 else 0, lparam)
    time.sleep(0.04)
print(f"clicked ({bx},{by})")
