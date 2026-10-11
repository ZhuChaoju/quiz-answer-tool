# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"tools\test_text_modules.py"
s = open(p, encoding="utf-8").read()
old = """    img = Image.new("RGB", size, (40, 60, 50))
    d = ImageDraw.Draw(img)
    d.rectangle(dialog, fill=(168, 164, 210))
    font = ImageFont.truetype(find_font(22), 22)"""
new = """    img = Image.new("RGB", size, (40, 60, 50))
    d = ImageDraw.Draw(img)
    d.rectangle(dialog, fill=(168, 164, 210))
    # 画标题栏文字（乡试/会试/灯谜），位置在对话框顶部
    title_font = ImageFont.truetype(find_font(18), 18)
    dl, dt, dr_, db_ = dialog
    title_text = "乡试" if "xiangshi" in path else ("会试" if "huishi" in path else "灯谜")
    tw = d.textlength(title_text, font=title_font)
    d.text(((dl + dr_ - tw) / 2, dt + 6), title_text, fill=(200, 200, 220), font=title_font)
    font = ImageFont.truetype(find_font(22), 22)"""
assert old in s, "render pattern"
s = s.replace(old, new, 1)
ast.parse(s)
open(p, "w", encoding="utf-8").write(s)
print("render_dialog title added")
