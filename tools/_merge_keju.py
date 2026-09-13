# -*- coding: utf-8 -*-
"""任务1: 合并乡试/会试为单个'科举'模块（三套布局变体自动探测）。"""
import ast
import io
import json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = r"D:\work\quiz-answer-tool"

# 读三套实测 ROI
xiangshi = json.load(open(rf"{ROOT}\banks\keju\modules\keju_xiangshi.json", encoding="utf-8-sig"))
huishi = json.load(open(rf"{ROOT}\banks\keju\modules\keju_huishi.json", encoding="utf-8-sig"))

merged = {
    "id": "keju",
    "name": "科举大赛（乡试/会试）",
    "type": "text",
    "bank": "questions.json",
    "question_anchor": "题目\\s*[:：]",
    "noise": ["这一关考的是", "请指点迷津", "使用法宝"],
    "gate_keywords": ["礼部考题", "御前科举", "逍遥生", "龙太子"],
    "merge_threshold": 0.6,
    "roi_variants": [
        {"when": "乡试布局(实测09-13)",
         "question": xiangshi["roi"]["question"].__str__() if False else xiangshi["roi"]["question"],
         "option": xiangshi["roi"]["option"]},
        {"when": "会试布局(实测09-13)",
         "question": huishi["roi"]["question"],
         "option": huishi["roi"]["option"]},
    ],
    "roi": {  # 兼容字段：默认取第一变体
        "question": xiangshi["roi"]["question"],
        "option": xiangshi["roi"]["option"],
    },
    "calibration": "2026-09-13 三套布局均为实机程序化检测: 乡试(题面515,373; 选项2x2@515,547/777,547), "
                   "会试有图(题面655,338), 会试无图(题面515,373 同乡试位置); 拖动过框则解锁校准保存",
    "locked": True,
}
# 变体里的 roi 直接用 dict
for v in merged["roi_variants"]:
    v["question"] = dict(v["question"])
    v["option"] = dict(v["option"])

open(rf"{ROOT}\banks\keju\modules\keju.json", "w", encoding="utf-8").write(
    json.dumps(merged, ensure_ascii=False, indent=2))
print("keju.json (merged module) written")

# 删除旧的两个分模块
import os
for f in (rf"{ROOT}\banks\keju\modules\keju_huishi.json", rf"{ROOT}\banks\keju\modules\keju_xiangshi.json"):
    os.remove(f)
print("old module jsons removed")
