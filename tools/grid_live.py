# -*- coding: utf-8 -*-
"""给实测帧叠加百分比网格，测量乡试对话框几何。"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from PIL import Image, ImageDraw

img = Image.open(r"D:\work\_downloads\live_now.png").convert("RGB")
W, H = img.size
grid = img.copy()
d = ImageDraw.Draw(grid)
for i in range(1, 20):
    x = W * i // 20
    d.line((x, 0, x, H), fill=(255, 0, 0), width=1)
    d.text((x + 2, 2), str(round(i * 5)))
for i in range(1, 20):
    y = H * i // 20
    d.line((0, y, W, y), fill=(255, 0, 0), width=1)
    d.text((2, y + 2), str(round(i * 5)))
grid.save(r"D:\work\_downloads\xiangshi_grid.png")
print("saved", W, H)
