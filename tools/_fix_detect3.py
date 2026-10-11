# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"tools\detect_game_now.py"
s = open(p, encoding="utf-8").read()
# 阈值降到 150，并保存标注图
s = s.replace("mask = lum.mean(axis=2) > 160", "mask = lum.mean(axis=2) > 150")
old = 'img.save(r"D:\\work\\_downloads\\game_now.png")'
new = '''img.save(r"D:\\work\\_downloads\\game_now.png")
from PIL import ImageDraw

_vis = img.copy()
_d = ImageDraw.Draw(_vis)
for area, bw, bh, l, t, r, b, fill in comps[:8]:
    _d.rectangle((l, t, r, b), outline=(255, 0, 0), width=2)
_vis.save(r"D:\\work\\_downloads\\game_now_boxes.png")'''
assert old in s
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(s)
ast.parse(s)
print("debug save added")
