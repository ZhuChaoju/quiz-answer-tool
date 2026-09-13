# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"src\quiz_answer_tool\activities\icon.py"
s = open(p, encoding="utf-8").read()

old = """    def add(self, h: str, name: str) -> None:
        \"\"\"录入实拍哈希：同名的旧哈希保留，新哈希追加（去重）。\"\"\"
        if h in self._by_name.get(name, []):
            return
        self._entries.append({"name": name, "hash": h})
        self._by_name.setdefault(name, [])
        self._by_name[name].append(h)
        self._table.append((name, h, int(h, 16)))"""
new = """    def add(self, h: str, name: str) -> None:
        \"\"\"录入实拍哈希：同名的旧哈希保留，新哈希追加（去重）。\"\"\"
        if h in self._by_name.get(name, []):
            return
        self._entries.append({"name": name, "hash": h})
        self._by_name.setdefault(name, [])
        self._by_name[name].append(h)
        self._table.append((name, h, int(h, 16)))

    def names_with_answer(self, answer: str) -> list[str]:
        \"\"\"返回答案（技能名）等于该文本的所有条目名——录入查重用。\"\"\"
        return [n for n in self._by_name if n == answer]

    def remove_name(self, name: str) -> int:
        \"\"\"删除该技能名的全部哈希条目，返回删除数。\"\"\"
        n0 = len(self._entries)
        self._entries = [e for e in self._entries if e.get("name") != name]
        self._table = [t for t in self._table if t[0] != name]
        self._by_name.pop(name, None)
        return n0 - len(self._entries)"""
assert old in s, "add pattern"
s = s.replace(old, new, 1)
ast.parse(s)
open(p, "w", encoding="utf-8").write(s)
print("IconBank names_with_answer/remove_name added")
