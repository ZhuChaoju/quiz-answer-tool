# -*- coding: utf-8 -*-
"""构建教师节看图说话图标库 banks/teachers/icons.json。

素材来源：梦幻西游官网 xyq.163.com 技能图标表（网易官方 CDN nie.res.netease.com），
此前由解析脚本抓取到 D:\\work\\_downloads\\skill_icons\\<技能名>.png，本脚本：
  1. 过滤网页解析噪声（横幅图/非技能名）；
  2. 复制干净图标到 banks/teachers/icons/（素材库随库走）；
  3. 用与运行时完全一致的管线（icon.icon_hash）构建哈希索引。

用法: python tools/build_icon_bank.py <skill_icons目录>
"""

from __future__ import annotations

import json
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from quiz_answer_tool.activities.icon import icon_hash  # noqa: E402

BAD_CHARS = "，。：：、（）()?？!!.． "


def is_valid_name(name: str) -> bool:
    if not (2 <= len(name) <= 8):
        return False
    if any(ch.isascii() for ch in name):  # CTRL+F 之类
        return False
    return not any(ch in BAD_CHARS for ch in name)


def main() -> None:
    src = sys.argv[1] if len(sys.argv) > 1 else r"D:\work\_downloads\skill_icons"
    root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    icons_dir = os.path.join(root, "banks", "teachers", "icons")
    os.makedirs(icons_dir, exist_ok=True)

    entries = []
    copied = skipped = 0
    for fn in sorted(os.listdir(src)):
        if not fn.lower().endswith(".png"):
            continue
        name = os.path.splitext(fn)[0]
        if not is_valid_name(name):
            skipped += 1
            continue
        path = os.path.join(src, fn)
        img = Image.open(path)
        if img.width > 200 or img.height > 200:  # 网页横幅等大图
            skipped += 1
            continue
        img.close()
        dst = os.path.join(icons_dir, fn)
        if os.path.abspath(path) != os.path.abspath(dst):
            shutil.copyfile(path, dst)
            copied += 1
        entries.append({"name": name, "hash": icon_hash(Image.open(dst))})

    out = os.path.join(root, "banks", "teachers", "icons.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=0)
    print(f"icons: {len(entries)} entries, copied {copied}, skipped {skipped} -> {out}")


if __name__ == "__main__":
    from PIL import Image  # noqa: F401  (延迟导入，便于 --help 场景)
    main()
