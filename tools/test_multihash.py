# -*- coding: utf-8 -*-
"""同一技能名多个图标变体：录入两个不同哈希，两个都要能命中。"""
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from quiz_answer_tool.activities.icon import IconBank

bank = IconBank([{"name": "养生之道", "hash": "a" * 64}, {"name": "破釜沉舟", "hash": "b" * 64}])

# 场景：破釜沉舟有两个不同图标的变体（官方素材版 + 游戏实拍版1 + 游戏实拍版2）
bank.add("c" * 64, "破釜沉舟")   # 实拍变体1
bank.add("d" * 64, "破釜沉舟")   # 实拍变体2
print("破釜沉舟 哈希数:", len(bank._by_name["破釜沉舟"]))

# 三个变体都要能命中（选项过滤路径 = min_distance）
for i, v in enumerate(("b" * 64, "c" * 64, "d" * 64)):
    d = bank.min_distance(v, "破釜沉舟")
    hit = d is not None and d <= 100
    print(f"变体{i + 1}: 距离={d} {'OK' if hit and d == 0 else 'FAIL'}")

# 反例：别的图标不能因为多哈希而误命中
d_other = bank.min_distance("e" * 64, "破釜沉舟")
print(f"无关图标距离={d_other}（应远大于阈值）")

# 全库兜底路径
near = bank.nearest("c" * 64)
print(f"全库最近邻: {near} {'OK' if near[0] == '破釜沉舟' and near[1] == 0 else 'FAIL'}")

# 持久化往返
import json
import tempfile

p = os.path.join(tempfile.gettempdir(), "test_icons.json")
bank.save(p)
bank2 = IconBank.load(p)
print(f"重新加载后: 总条目={len(bank2)}, 破釜沉舟哈希数={len(bank2._by_name['破釜沉舟'])}")
os.remove(p)
