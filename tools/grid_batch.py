# -*- coding: utf-8 -*-
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from PIL import Image, ImageDraw

d = r"C:\Users\zcj\Downloads\截图\科举"
for fn in ("screenshot-20260913-140308.png", "screenshot-20260913-142540.png",
           "screenshot-20260913-142719.png", "screenshot-20260913-143359.png"):
    p = os.path.join(d, fn) if False else d + "\\" + fn
    img = Image.open(p).convert("RGB")
    W, H = img.size
    grid = img.copy()
    dr = ImageDraw.Draw(grid)
    for i in range(1, 40):
        x = W * i // 40
        dr.line((x, 0, x, H), fill=(255, 0, 0), width=1)
        if i % 4 == 0:
            dr.text((x + 2, 2), str(round(x / W * 100)), fill=(255, 255, 0))
    for i in range(1, 40):
        y = H * i // 40
        dr.line((0, y, W, y), fill=(255, 0, 0), width=1)
        if i % 4 == 0:
            dr.text((2, y + 2), str(round(y / H * 100)), fill=(255, 255, 0))
    out = r"D:\work\_downloads\grid_" + fn
    grid.save(out)
    print(fn, W, H)
