# -*- coding: utf-8 -*-
"""还原工具窗口尺寸 + 验证破釜沉舟录入。"""
import ctypes
import io
import json
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
user32 = ctypes.windll.user32

hwnd = user32.FindWindowW(None, "答题识别工具（仅展示，不操作游戏）")
print("hwnd:", hwnd)
if hwnd:
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    print("restored to normal size")

time.sleep(0.3)
p = r"dist\release\banks\teachers\icons.json"
entries = json.load(open(p, encoding="utf-8-sig"))
hit = [e for e in entries if e.get("name") == "破釜沉舟"]
print("破釜沉舟 entry:", hit if hit else "未找到")
print("total entries:", len(entries))
