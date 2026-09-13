# -*- coding: utf-8 -*-
"""实况帧精确检测：会试题面白框 + 选项淡紫框 → 输出百分比 ROI。"""
import io
import os
import sys
from collections import deque

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import numpy as np
from PIL import Image

from quiz_answer_tool import screen

src = screen.find_game_source("梦幻西游")
frame, _ = screen.capture(src)
W, H = frame.size
print("window:", W, H)
frame.save(r"D:\work\_downloads\huishi_live.png")

arr = np.asarray(frame, dtype=np.float64)
lum = arr.mean(axis=2)

# 检测范围：对话框大致区域（全图 y 10%..90%，x 5%..98%）
Y0, Y1 = int(H * 0.10), int(H * 0.90)
X0, X1 = int(W * 0.05), int(W * 0.98)
sub = (lum[Y0:Y1, X0:X1] > 170)  # 亮色（题面纸白 ~230，选项淡紫 ~205）

seen = np.zeros_like(sub, dtype=bool)
hh, ww = sub.shape
comps = []
for sy in range(hh):
    for sx in range(ww):
        if not sub[sy, sx] or seen[sy, sx]:
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
                if 0 <= ny < hh and 0 <= nx < ww and sub[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    q.append((ny, nx))
        bw, bh = max_x - min_x + 1, max_y - min_y + 1
        if bw * bh < 4000:  # 过滤小元素
            continue
        fill = n / (bw * bh)
        comps.append((bw * bh, bw, bh, X0 + min_x, Y0 + min_y, X0 + max_x + 1, Y0 + max_y + 1, fill))

comps.sort(key=lambda c: -c[0])
print("大亮色块：")
for area, bw, bh, l, t, r, b, fill in comps[:6]:
    print(f"  px=({l},{t})-({r},{b}) {bw}x{bh} fill={fill:.2f}  "
          f"%=({l / W * 100:.2f},{t / H * 100:.2f},w{bw / W * 100:.2f},h{bh / H * 100:.2f})")
