# -*- coding: utf-8 -*-
"""量网图会试对话框几何 → 推算 1036x831 实测窗口下的居中 ROI。"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from PIL import Image, ImageDraw

img = Image.open(r"D:\work\_downloads\keju_huishi_web.jpg").convert("RGB")
W, H = img.size
print("web size:", W, H)

# 对话框深蓝边框色，先粗定位：扫描中轴线上的暗色段
px = img.load()
# 逐行找“几乎整行都接近暗蓝/深色”的行 → 对话框上下边界；同理找列
def row_dark_ratio(y, x0, x1):
    n = j = 0
    for x in range(x0, x1, 4):
        r, g, b = px[x, y]
        n += 1
        if r < 90 and g < 90 and b < 110:
            j += 1
    return j / max(n, 1)

def col_dark_ratio(x, y0, y1):
    n = j = 0
    for y in range(y0, y1, 4):
        r, g, b = px[x, y]
        n += 1
        if r < 90 and g < 90 and b < 110:
            j += 1
    return j / max(n, 1)

# 先画一张缩略图目测对话框大致范围
thumb = img.resize((W // 2, H // 2))
d = ImageDraw.Draw(thumb)
for gx in range(0, W // 2, 50):
    d.line((gx, 0, gx, H // 2), fill=(255, 0, 0), width=1)
    d.text((gx + 2, 2), str(gx * 2), fill=(255, 255, 0))
for gy in range(0, H // 2, 50):
    d.line((0, gy, W // 2, gy), fill=(255, 0, 0), width=1)
    d.text((2, gy + 2), str(gy * 2), fill=(255, 255, 0))
thumb.save(r"D:\work\_downloads\huishi_grid.png")
print("saved huishi_grid.png")
