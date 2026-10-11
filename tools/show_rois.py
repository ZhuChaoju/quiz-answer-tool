import json
import io
import os
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import numpy as np
from PIL import Image, ImageDraw

from quiz_answer_tool import screen

sources = [x for x in screen.list_sources() if x.kind == "window" and "ONLINE" in x.name.upper()]
frame, _ = screen.capture(sources[0])
img = frame.convert("RGB")
W, H = img.size
print("游戏窗口:", W, H)
img.save(r"D:\work\_downloads\exam_now.png")

# 叠加当前 ROI 位置

import json as _j
d_json = _j.load(open(r"D:\work\quiz-answer-tool\banks\keju\modules\keju.json", encoding="utf-8-sig"))
roi = d_json.get("roi", {})
vis = img.copy()
dd = ImageDraw.Draw(vis)
for key, color in (("question", (0, 255, 0)), ("option", (0, 200, 255)), ("search", (255, 255, 0))):
    r = roi.get(key)
    if not r:
        continue
    l, t = int(W * r["x"] / 100), int(H * r["y"] / 100)
    rr, bb = int(W * (r["x"] + r["w"]) / 100), int(H * (r["y"] + r["h"]) / 100)
    dd.rectangle((l, t, rr, bb), outline=color, width=2)
    dd.text((l + 2, t + 2), key, fill=color)
vis.save(r"D:\work\_downloads\exam_rois.png")
print("saved exam_rois.png")
