# -*- coding: utf-8 -*-
"""merge_threshold 回归测试：折行合并阈值按模块配置生效。

固定一组选项 OCR 检测框（两行文本垂直距离 20px、行高 40px）：
- 阈值 0.6：20 < 24 → 合并成一行（科举折行题面行为）
- 阈值 0.4：20 > 16 → 保持两行（更严格的模块行为）
同时断言模块配置里的 merge_threshold 正确装配到模块实例。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from quiz_answer_tool import ocr
from quiz_answer_tool.activities import load_modules

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def make_boxes():
    """两行选项：垂直中心距 20px，行高 40px（可被 0.6 合并、被 0.4 分开）。"""
    from quiz_answer_tool.ocr import Line

    a = Line(text="火眼金睛", center_x=30, center_y=20, confidence=0.9, width=60, height=40)
    b = Line(text="调息", center_x=100, center_y=40, confidence=0.9, width=40, height=40)
    return [a, b]


failures = []

# 1) 阈值直接生效
merged = ocr.merge_lines(make_boxes(), merge_threshold=0.6)
separate = ocr.merge_lines(make_boxes(), merge_threshold=0.4)
if len(merged) != 1 or merged[0].text != "火眼金睛调息":
    failures.append(f"0.6 应合并成一行: {[(l.text) for l in merged]}")
if len(separate) != 2:
    failures.append(f"0.4 应保持两行: {[(l.text) for l in separate]}")
print(f"merge_lines 阈值: 0.6 -> {len(merged)} 行, 0.4 -> {len(separate)} 行")

# 2) 模块配置装配：keju 默认 0.6，teachers 显式 0.5
mods = {m.id: m for m in load_modules(os.path.join(ROOT, "banks"))}
if abs(mods["keju_huishi"].merge_threshold - 0.6) > 1e-9:
    failures.append(f"keju_huishi merge_threshold 应为默认 0.6: {mods['keju_huishi'].merge_threshold}")
if abs(mods["teachers"].merge_threshold - 0.5) > 1e-9:
    failures.append(f"teachers merge_threshold 应为 0.5: {mods['teachers'].merge_threshold}")
print(f"keju_huishi={mods['keju_huishi'].merge_threshold}, teachers={mods['teachers'].merge_threshold}")

# 3) 各模块阈值锁定行为：同一组框在 keju(0.6) 下合并、teachers(0.5) 下不合并
k = ocr.merge_lines(make_boxes(), mods["keju_huishi"].merge_threshold)
t = ocr.merge_lines(make_boxes(), mods["teachers"].merge_threshold)
if not (len(k) == 1 and len(t) == 2):
    failures.append(f"模块阈值行为不符: keju={len(k)} 行, teachers={len(t)} 行")
print(f"模块差异: keju(0.6) -> {len(k)} 行(合并), teachers(0.5) -> {len(t)} 行(分开)")

if failures:
    print("FAIL:", failures)
    sys.exit(1)
print("merge_threshold regression: PASS")
