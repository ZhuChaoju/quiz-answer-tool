# -*- coding: utf-8 -*-
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"tools\test_text_modules.py"
s = open(p, encoding="utf-8").read()

# 模块引用更新：keju_huishi/keju_xiangshi 合并为 keju
s = s.replace('mods["keju_huishi"]', 'mods["keju"]')
s = s.replace('mods["keju_xiangshi"]', 'mods["keju"]')
# 断言集合更新
old_assert = 'assert set(mods) == {"teachers", "keju_huishi", "keju_xiangshi", "yuanxiao"}, mods.keys()'
new_assert = 'assert set(mods) == {"teachers", "keju", "yuanxiao"}, mods.keys()'
if old_assert in s:
    s = s.replace(old_assert, new_assert, 1)
open(p, "w", encoding="utf-8").write(s)
print("test updated")
