# -*- coding: utf-8 -*-
import ctypes
import json
import time

p = r"D:\work\quiz-answer-tool\dist\release\config.json"
d = json.load(open(p, encoding="utf-8-sig"))
d["ui"]["autostart"] = True
json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("autostart back on")

user32 = ctypes.windll.user32
hwnd = user32.FindWindowW(None, "答题识别工具（仅展示，不操作游戏）")
print("hwnd:", hwnd)


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


rect = RECT()
user32.GetClientRect(hwnd, ctypes.byref(rect))
bx, by = rect.right - 130, 8
lparam = (by << 16) | bx
for msg in (0x0200, 0x0201, 0x0202):
    user32.PostMessageW(hwnd, msg, 1 if msg == 0x0201 else 0, lparam)
    time.sleep(0.04)
print("clicked Start at", bx, by)
