# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"src\quiz_answer_tool\viewer.py"
s = open(p, encoding="utf-8").read()

# 识别后：无题目时静默跳过，不更新 UI（不再跳动）
old = """                    try:
                        result = mod.recognize(frame, ocr_cfg)
                    except Exception as exc:
                        self._result_queue.put(("error", f"识别失败: {exc}"))
                        return
                    self._result_queue.put(("result", result))"""
new = """                    try:
                        result = mod.recognize(frame, ocr_cfg)
                    except Exception as exc:
                        self._result_queue.put(("error", f"识别失败: {exc}"))
                        return
                    # 无题目时静默跳过，不更新 UI（避免动画导致的持续跳动）
                    if result.state != "no_dialog":
                        self._result_queue.put(("result", result))"""
assert old in s, "pattern not found"
s = s.replace(old, new, 1)
ast.parse(s)
open(p, "w", encoding="utf-8").write(s)
print("no_dialog silent skip ok")
