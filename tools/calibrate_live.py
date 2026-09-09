# -*- coding: utf-8 -*-
"""实况校准：抓游戏窗口 → 连通域定位答题图标 → 按当前窗口尺寸换算百分比 ROI →
写回 banks/teachers/module.json（仓库与 release 各一份）。"""

import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from PIL import Image

from quiz_answer_tool.activities.icon import locate_icon
from quiz_answer_tool import screen

# 1) 找游戏主窗口（区分于"梦幻西游 聊天窗口"悬浮窗）
sources = [s for s in screen.list_sources() if s.kind == "window" and "ONLINE" in s.name.upper()]
if not sources:
    print("game window not found")
    sys.exit(1)
src = sources[0]
print("window:", src.name)

# 2) 截图（进度条对话要卡在答题界面）
frame, rect = screen.capture(src)
print("frame size:", frame.size)
frame.save(r"D:\work\_downloads\live_calib.png")

# 3) 定位图标（当前搜索窗）
PANEL = (162, 168, 210)
search = {"x": 30.0, "y": 22.0, "w": 30.0, "h": 40.0}  # 宽松搜索窗
box = locate_icon(frame, search, PANEL)
print("icon bbox:", box)
if box is None:
    print("icon NOT located - 答题框可能没开或被遮挡")
    sys.exit(2)

w, h = frame.size
il, it, ir, ib = box
icon_roi = {"x": round((il - 3) / w * 100, 2), "y": round((it - 3) / h * 100, 2),
            "w": round((ir - il + 6) / w * 100, 2), "h": round((ib - it + 6) / h * 100, 2)}
# 搜索窗：图标周边 ±9% 宽 / ±10% 高（覆盖对话框被拖动的范围）
icon_cx, icon_cy = (il + ir) / 2 / w * 100, (it + ib) / 2 / h * 100
search_roi = {"x": round(icon_cx - 9, 2), "y": round(icon_cy - 10, 2), "w": 18.0, "h": 20.0}

# 4) 选项区：对话框内图标右下的 2x2 网格。
# 以 1024x768 校准（220110）：对话框原点(210,195)，图标(419,261)，选项(400,363)-(795,487)
# → 图标到选项区偏移：dx=-19..+376, dy=+102..+226（相对图标左上角）
dl, dt = il, it
ol = il - 19
ot = it + 102
orr = il + 376
ob = it + 226
option_roi = {"x": round(ol / w * 100, 2), "y": round(ot / h * 100, 2),
              "w": round((orr - ol) / w * 100, 2), "h": round((ob - ot) / h * 100, 2)}

print("icon_roi  =", icon_roi)
print("search_roi=", search_roi)
print("option_roi=", option_roi)

if "--write" in sys.argv:
    for base in (os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")),
                 r"D:\work\quiz-answer-tool\dist\release"):
        p = os.path.join(base, "banks", "teachers", "module.json")
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        data["roi"]["icon"] = icon_roi
        data["roi"]["search"] = search_roi
        data["roi"]["option"] = option_roi
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("written:", p)
