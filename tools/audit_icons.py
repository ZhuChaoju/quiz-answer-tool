# -*- coding: utf-8 -*-
"""图标库审计：展示指定条目 + 找出被实拍哈希覆盖/可能录串的条目。"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from PIL import Image

from quiz_answer_tool.activities.icon import hamming, icon_hash

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ICON_DIR = os.path.join(ROOT, "banks", "teachers", "icons")
entries = json.load(open(os.path.join(ROOT, "banks", "teachers", "icons.json"), encoding="utf-8-sig"))
by_name = {e["name"]: e for e in entries}

# 每个条目重算官方素材哈希
asset_hash = {}
for e in entries:
    p = os.path.join(ICON_DIR, e["name"] + ".png")
    if os.path.exists(p):
        asset_hash[e["name"]] = icon_hash(Image.open(p))
    else:
        asset_hash[e["name"]] = None

# ---- 指定条目展示 ----
for name in ("破釜沉舟", "火眼金睛"):
    e = by_name.get(name)
    print(f"== {name} ==")
    if not e:
        print("  库中无此条目")
        continue
    ah = asset_hash.get(name)
    same = ah is not None and e["hash"] == ah
    print(f"  当前哈希: {e['hash'][:16]}...  与官方素材哈希{'一致(未动过)' if same else '不同(已被实拍覆盖)'}")
    if ah and not same:
        print(f"  实拍vs官方素材距离: {hamming(e['hash'], ah)}")
    # 实拍哈希在全库官方素材里的最近邻（排除自己）——检查是否录串
    best, bd = None, 1 << 30
    for n2, h2 in asset_hash.items():
        if n2 == name or h2 is None:
            continue
        d = hamming(e["hash"], h2)
        if d < bd:
            bd, best = d, n2
    print(f"  实拍哈希的最近官方素材: {best} (距离 {bd})")
    p = os.path.join(ICON_DIR, name + ".png")
    if os.path.exists(p):
        img = Image.open(p).convert("RGBA")
        bg = Image.new("RGBA", img.size, (162, 168, 210, 255))
        bg.paste(img, (0, 0), img)
        s = bg.convert("RGB").resize((img.width * 5, img.height * 5), Image.NEAREST)
        s.save(rf"D:\work\_downloads\icon_{name}.png")
        print(f"  官方图标图已存: D:\\work\\_downloads\\icon_{name}.png")
    print()

# ---- 全库审计：实拍覆盖过的条目 + 录串嫌疑 ----
print("== 全库审计（实拍覆盖条目）==")
suspicious = []
for e in entries:
    name, h = e["name"], e["hash"]
    ah = asset_hash.get(name)
    if ah is None or h == ah:
        continue  # 未被覆盖
    d_own = hamming(h, ah)
    best, bd = None, 1 << 30
    for n2, h2 in asset_hash.items():
        if n2 == name or h2 is None:
            continue
        d = hamming(h, h2)
        if d < bd:
            bd, best = d, n2
    flag = "  <-- 嫌疑: 实拍哈希更像别人的素材!" if bd < d_own else ""
    print(f"  {name}: 实拍vs自己素材={d_own}, 最近他人素材={best}({bd}){flag}")
    if bd < d_own:
        suspicious.append((name, best, bd, d_own))

print(f"\n录串嫌疑条目: {len(suspicious)} 个")
for name, other, bd, d_own in suspicious:
    print(f"  {name} -> 更像 {other} (距{bd} < 自身{d_own})")
