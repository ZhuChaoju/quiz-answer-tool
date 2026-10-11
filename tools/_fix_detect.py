# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"tools\detect_big.py"
s = open(p, encoding="utf-8").read()
# 加 BFS 提前退出（只找前 8 个大连通域即可）
s = s.replace(
    "from collections import deque",
    "from collections import deque\nimport ctypes",
)
# 限制搜索区域为中部（避开全屏边缘）
old_lim = "hh, ww = mask.shape"
new_lim = """hh, ww = mask.shape
# 限制在画面中部（对话框所在区域），避免边缘干扰
pad_y = int(hh * 0.1)
pad_x = int(ww * 0.1)
sub_mask = mask[pad_y:hh - pad_y, pad_x:ww - pad_x]
mask = sub_mask
y_off, x_off = pad_y, pad_x
hh, ww = mask.shape"""
assert old_lim in s
s = s.replace(old_lim, new_lim, 1)
# 坐标偏移
old_comp = "        comps.append((bw * bh, bw, bh, min_x, min_y, max_x + 1, max_y + 1, fill))"
new_comp = "        comps.append((bw * bh, bw, bh, x_off + min_x, y_off + min_y, x_off + max_x + 1, y_off + max_y + 1, fill))"
assert old_comp in s
s = s.replace(old_comp, new_comp, 1)
old_print = "for area, bw, bh, l, t, r, b, fill in comps[:8]:"
new_print = "for area, bw, bh, l, t, r, b, fill in comps[:8]:  # l=px+t..."
assert old_print in s
s = s.replace(old_print, new_print, 1)
ast.parse(s)
open(p, "w", encoding="utf-8").write(s)
print("offset ok")
