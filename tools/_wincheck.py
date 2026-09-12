# -*- coding: utf-8 -*-
import ctypes
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
user32 = ctypes.windll.user32
print("tool hwnd:", user32.FindWindowW(None, "答题识别工具（仅展示，不操作游戏）"))
print("overlay hwnd:", user32.FindWindowW(None, "答题浮窗"))
