# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"src\quiz_answer_tool\viewer.py"
s = open(p, encoding="utf-8").read()

old = """                try:
                    frame, _ = screen.capture(source)
                    gate_crop = mod.rois[gate_key].crop(frame, pad=0.02)
                except Exception as exc:
                    self._result_queue.put(("error", f"截图失败: {exc}"))
                    continue
                cur = _dhash(gate_crop)
                if cur == last_hash:
                    continue
                last_hash = cur"""

new = """                try:
                    frame, _ = screen.capture(source)
                    # 变化闸门覆盖题面/图标 + 选项两个区域：
                    # 同图标但选项换位时也要重新识别，否则红框残留指错位置
                    gate_main = _dhash(mod.rois[gate_key].crop(frame, pad=0.02))
                    gate_opt = _dhash(mod.rois["option"].crop(frame, pad=0.02))
                    cur = (gate_main, gate_opt)
                except Exception as exc:
                    self._result_queue.put(("error", f"截图失败: {exc}"))
                    continue
                if cur == last_hash:
                    continue
                last_hash = cur"""

assert old in s, "pattern not found"
s = s.replace(old, new)
# last_hash 类型改为元组，初始化同步
s = s.replace("last_hash: int | None = None\n            last_mod_id: str | None = None",
              "last_hash: tuple | None = None\n            last_mod_id: str | None = None")
open(p, "w", encoding="utf-8").write(s)
ast.parse(s)
print("gate fix applied, syntax ok")
