# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"src\quiz_answer_tool\viewer.py"
s = open(p, encoding="utf-8").read()

old = """        self._running = True
        self._start_btn.config(text="停止")
        self._start_threads(source)"""
new = """        self._running = True
        self._start_btn.config(text="停止")
        self._save_config()  # 点开始即保存当前活动/设置，异常退出也不丢
        self._start_threads(source)"""
assert old in s
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(s)
ast.parse(s)
print("toggle save added, syntax ok")
