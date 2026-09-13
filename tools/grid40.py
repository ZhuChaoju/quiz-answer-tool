# -*- coding: utf-8 -*-
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from PIL import Image, ImageDraw

img = Image.open(r"D:\work\_downloads\huishi_live.png").convert("RGB")
W, H = img.size
grid = img.copy()
d = ImageDraw.Draw(grid)
for i in range(1, 40):
    x = W * i // 40
    d.line((x, 0, x, H), fill=(255, 0, 0), width=1)
    if i % 2 == 0:
        d.text((x + 2, 2), str(round(x / W * 100, 1)), fill=(255, 255, 0))
for i in range(1, 40):
    y = H * i // 40
    d.line((0, y, W, y), fill=(255, 0, 0), width=1)
    if i % 2 == 0:
        d.text((2, y + 2), str(round(y / H * 100, 1)), fill=(255, 255, 0))
grid.save(r"D:\work\_downloads\huishi_grid40.png")
print("saved", W, H)
