# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"tools\detect_big.py"
s = open(p, encoding="utf-8").read()
# 改为抓游戏窗口
s = s.replace(
    'from quiz_answer_tool.activities import load_modules',
    'from quiz_answer_tool.activities import load_modules\nfrom quiz_answer_tool import screen',
)
s = s.replace(
    'SRC = r"C:\\Users\\zcj\\Downloads\\截图\\科举\\乡试\\screenshot-20260913-142206_810.png"\nimg = Image.open(SRC).convert("RGB")\nW, H = img.size\nprint("size:", W, H)',
    'sources = [x for x in screen.list_sources() if x.kind == "window" and "ONLINE" in x.name.upper()]\nif not sources:\n    sys.exit("游戏窗口未找到")\nframe, _ = screen.capture(sources[0])\nimg = frame.convert("RGB")\nW, H = img.size\nprint("游戏窗口:", sources[0].name[:30], W, H)\nimg.save(r"D:\\work\\_downloads\\game_now.png")'
)
open(p, "w", encoding="utf-8").write(s)
ast.parse(s)
print("detect_big.py ok")
