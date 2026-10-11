# -*- coding: utf-8 -*-
import io
import os
import sys
from collections import deque

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import numpy as np
from PIL import Image, ImageDraw

from quiz_answer_tool import screen

sources = [x for x in screen.list_sources() if x.kind == "window" and "ONLINE" in x.name.upper()]
if not sources:
    sys.exit("游戏窗口未找到")
frame, _ = screen.capture(sources[0])
img = frame.convert("RGB")
W, H = img.size
print("游戏窗口:", sources[0].name[:30], W, H)

lum = np.asarray(img, dtype=np.float64)
mask = lum.mean(axis=2) > 150
seen = np.zeros_like(mask, dtype=bool)
comps = []
hh, ww = mask.shape
for sy in range(hh):
    for sx in range(ww):
        if not mask[sy, sx] or seen[sy, sx]:
            continue
        q = deque([(sy, sx)])
        seen[sy, sx] = True
        n = 0
        min_y = max_y = sy
        min_x = max_x = sx
        while q:
            y, x = q.popleft()
            n += 1
            min_y, max_y = min(min_y, y), max(max_y, y)
            min_x, max_x = min(min_x, x), max(max_x, x)
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < hh and 0 <= nx < ww and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    q.append((ny, nx))
        bw, bh = max_x - min_x + 1, max_y - min_y + 1
        if bw * bh < 15000:
            continue
        fill = n / (bw * bh)
        comps.append((bw * bh, bw, bh, min_x, min_y, max_x + 1, max_y + 1, fill))

comps.sort(key=lambda c: -(c[1] * c[2]))
print("大亮色块：")
vis = img.copy()
from PIL import ImageDraw

dd = ImageDraw.Draw(vis)
for area, bw, bh, l, t, r, b, fill in comps[:8]:
    print(f"  px=({l},{t})-({r},{b}) {bw}x{bh} fill={fill:.2f}")
    dd.rectangle((l, t, r, b), outline=(255, 0, 0), width=3)
vis.save(r"D:\work\_downloads\game_boxes.png")
print("saved game_boxes.png")
