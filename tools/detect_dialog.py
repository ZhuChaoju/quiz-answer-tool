# -*- coding: utf-8 -*-
"""程序化检测乡试对话框：白色题面框 + 淡紫选项框的精确位置（像素与百分比）。"""
import io
import sys
from collections import deque

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import numpy as np
from PIL import Image

img = Image.open(r"D:\work\_downloads\live_now.png").convert("RGB")
W, H = img.size
region = np.asarray(img, dtype=np.float64)

# 亮色掩码（题面白框 ~235,选项框 ~200：都明显高于暗色背景）
lum = region.mean(axis=2)
mask = lum > 175

# 限定在对话框区域（y 15%..85%），排除顶部血条/右侧任务栏
y0, y1 = int(H * 0.15), int(H * 0.85)
x0, x1 = int(W * 0.05), int(W * 0.98)
mask[: y0 - 0] = False  # noqa
sub = mask[y0:y1, x0:x1]

seen = np.zeros_like(sub, dtype=bool)
comps = []
hh, ww = sub.shape
for sy in range(hh):
    for sx in range(ww):
        if not sub[sy, sx] or seen[sy, sx]:
            continue
        q = deque([(sy, sx)])
        seen[sy, sx] = True
        pts = []
        while q:
            y, x = q.popleft()
            pts.append((y, x))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < hh and 0 <= nx < ww and sub[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    q.append((ny, nx))
        if len(pts) < 2000:  # 过滤小字
            continue
        ys = [p[0] for p in pts]
        xs = [p[1] for p in pts]
        bw, bh = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
        comps.append((len(pts), bw, bh, x0 + min(xs), y0 + min(ys), x0 + max(xs) + 1, y0 + max(ys) + 1))

comps.sort(key=lambda c: -(c[1] * c[2]))
print("大亮色块（按面积排序）：")
for n, bw, bh, l, t, r, b in comps[:6]:
    print(f"  px=({l},{t})-({r},{b})  {bw}x{bh}  填充={n / (bw * bh):.2f}  "
          f"百分比=({l / W * 100:.1f},{t / H * 100:.1f},w{bw / W * 100:.1f},h{bh / H * 100:.1f})")
