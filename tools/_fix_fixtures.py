# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"tools\test_text_modules.py"
s = open(p, encoding="utf-8").read()
old = """    render_dialog(p1, size, (230, 100, 850, 660),
                  roi_rect(mx, "question", size), roi_rect(mx, "option", size),
                  f"第3题：{q1['question']}", ["3", "6", "9"], vertical=True)"""
new = """    render_dialog(p1, size, (230, 100, 850, 660),
                  roi_rect(mx, "question", size), roi_rect(mx, "option", size),
                  f"礼部考题，已答3题，答对3题。{q1['question']}", ["3", "6", "9"], vertical=True)"""
assert old in s, "p1"
s = s.replace(old, new, 1)
old2 = """    render_dialog(p2, size, (230, 100, 850, 660),
                  roi_rect(my, "question", size), roi_rect(my, "option", size),
                  f"灯谜：{q2['question']}", ["有去无回", "自身难保", "越洗越脏", "一步登天"])"""
new2 = """    render_dialog(p2, size, (230, 100, 850, 660),
                  roi_rect(my, "question", size), roi_rect(my, "option", size),
                  f"元宵节灯谜：{q2['question']}", ["有去无回", "自身难保", "越洗越脏", "一步登天"])"""
assert old2 in s, "p2"
s = s.replace(old2, new2, 1)
ast.parse(s)
open(p, "w", encoding="utf-8").write(s)
print("fixtures updated with realistic gate keywords")
