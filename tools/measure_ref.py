# -*- coding: utf-8 -*-
"""测量用户参考截图的会试对话框几何。"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from PIL import Image, ImageDraw

src = r"C:\Users\zcj\.zcode\cli\image-cache\sess_6499c656-d698-4726-8577-3ffe6005d047\image-c02bf8ccd9d5b1e2dca54337a3a930f2.png"
img = Image.open(src).convert("RGB")
W, H = img.size
print("reference size:", W, H)

# 叠加网格（每 5%）供目测
grid = img.resize((W * 2, H * 2), Image.LANCZOS)
d = ImageDraw.Draw(grid)
for i in range(1, 20):
    x = W * 2 * i // 20
    d.line((x, 0, x, H * 2), fill=(255, 0, 0), width=1)
    d.text((x + 2, 2), f"{i * 5}%", fill=(255, 255, 0))
for i in range(1, 20):
    y = H * 2 * i // 20
    d.line((0, y, W * 2, y), fill=(255, 0, 0), width=1)
    d.text((2, y + 2), f"{i * 5}%", fill=(255, 255, 0))
grid.save(r"D:\work\_downloads\huishi_ref_grid.png")
print("saved grid")
