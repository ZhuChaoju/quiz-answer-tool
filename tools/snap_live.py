# -*- coding: utf-8 -*-
"""抓游戏窗口，放大保存题目+选项区，供核对红框对位。"""
import io
import sys

sys.path.insert(0, r"D:\work\quiz-answer-tool\src")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from PIL import Image

from quiz_answer_tool import screen

sources = [s for s in screen.list_sources() if s.kind == "window" and "ONLINE" in s.name.upper()]
src = sources[0]
frame, rect = screen.capture(src)
print("window:", src.name, "size:", frame.size)
frame.save(r"D:\work\_downloads\live_now.png")

# 题面（图标+问题行）
q = frame.crop((300, 290, 900, 400))
q.resize((q.width * 2, q.height * 2), Image.LANCZOS).save(r"D:\work\_downloads\live_q.png")
# 选项区
o = frame.crop((380, 400, 860, 580))
o.resize((o.width * 2, o.height * 2), Image.LANCZOS).save(r"D:\work\_downloads\live_o.png")
print("saved")
