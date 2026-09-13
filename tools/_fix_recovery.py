# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"src\quiz_answer_tool\viewer.py"
s = open(p, encoding="utf-8").read()

# 1) 预览线程：截图失败/窗口失效时按标题找回游戏主窗口
old_prev = """                try:
                    frame, _ = screen.capture(source)
                    full_size = frame.size
                    rect = (0.0, 0.0, float(full_size[0]), float(full_size[1]))"""
new_prev = """                try:
                    frame, _ = screen.capture(source)
                    if frame.size[0] <= 1:
                        raise RuntimeError("窗口已失效")
                    source = screen.find_game_source() or source  # 游戏重启后自动找回窗口
                    full_size = frame.size
                    rect = (0.0, 0.0, float(full_size[0]), float(full_size[1]))"""
assert old_prev in s, "preview capture not found"
s = s.replace(old_prev, new_prev, 1)

# 2) 识别线程：同样找回
old_ocr = """                try:
                    frame, _ = screen.capture(source)
                    # 变化闸门覆盖题面/图标 + 选项两个区域：
                    # 同图标但选项换位时也要重新识别，否则红框残留指错位置
                    gate_main = _dhash(mod.rois[gate_key].crop(frame, pad=0.02))
                    gate_opt = _dhash(mod.rois["option"].crop(frame, pad=0.02))"""
new_ocr = """                try:
                    frame, _ = screen.capture(source)
                    if frame.size[0] <= 1:
                        raise RuntimeError("窗口已失效")
                    source = screen.find_game_source() or source  # 游戏重启后自动找回窗口
                    gate_main = _dhash(mod.rois[gate_key].crop(frame, pad=0.02))
                    gate_opt = _dhash(mod.rois["option"].crop(frame, pad=0.02))"""
assert old_ocr in s, "ocr capture not found"
s = s.replace(old_ocr, new_ocr, 1)

open(p, "w", encoding="utf-8").write(s)
ast.parse(s)
print("source auto-recovery added, syntax ok")
