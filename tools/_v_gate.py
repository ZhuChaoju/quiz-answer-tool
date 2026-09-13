# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"src\quiz_answer_tool\viewer.py"
s = open(p, encoding="utf-8").read()

old = """                try:
                    frame, _ = screen.capture(source)
                    if frame.size[0] <= 1:
                        raise RuntimeError("窗口已失效")
                    source = screen.find_game_source() or source  # 游戏重启后自动找回窗口
                    gate_main = _dhash(mod.rois[gate_key].crop(frame, pad=0.02))
                    gate_opt = _dhash(mod.rois["option"].crop(frame, pad=0.02))
                    cur = (gate_main, gate_opt)"""
new = """                try:
                    frame, _ = screen.capture(source)
                    if frame.size[0] <= 1:
                        raise RuntimeError("窗口已失效")
                    source = screen.find_game_source() or source  # 游戏重启后自动找回窗口
                    # 变化闸门覆盖全部布局变体的题面区 + 选项区：
                    gate_parts = [
                        _dhash(mod.rois[gate_key].crop(frame, pad=0.02)),
                        _dhash(mod.rois["option"].crop(frame, pad=0.02)),
                    ]
                    for rv in getattr(mod, "roi_variants", []):
                        if "question" in rv:
                            gate_parts.append(_dhash(rv["question"].crop(frame, pad=0.02)))
                    cur = tuple(gate_parts)"""
assert old in s, "gate pattern not found"
s = s.replace(old, new, 1)
ast.parse(s)
open(p, "w", encoding="utf-8").write(s)
print("viewer gate covers variants ok")
