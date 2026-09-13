# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ---- base.py: 白名单装配 ----
p = r"src\quiz_answer_tool\activities\base.py"
s = open(p, encoding="utf-8").read()
old = """        # 廉价预检阈值：题面区平均亮度低于该值判定无题目（0=禁用）
        self.presence_min_lum = float(data.get("presence_min_lum", 0) or 0)"""
new = """        # 廉价预检阈值：题面区平均亮度低于该值判定无题目（0=禁用）
        self.presence_min_lum = float(data.get("presence_min_lum", 0) or 0)
        # 答案白名单：名单内的答案允许在多个条目上重复（文件不存在则为空）
        wl = os.path.join(bank_dir, "whitelist.json")
        self.answer_whitelist: list[str] = []
        if os.path.exists(wl):
            try:
                import json

                self.answer_whitelist = [
                    str(x) for x in json.load(open(wl, encoding="utf-8-sig"))
                ]
            except Exception:
                self.answer_whitelist = []"""
assert old in s, "base pattern"
s = s.replace(old, new, 1)
ast.parse(s)
open(p, "w", encoding="utf-8").write(s)
print("base whitelist ok")
