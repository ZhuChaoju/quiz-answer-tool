# -*- coding: utf-8 -*-
"""从官方答题器 SPA 提取全部题目答案 → 合并到本地题库。"""
import ast
import io
import json
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from playwright.sync_api import sync_playwright

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://w.163.com/h5/xyq/dtk/index.html#/keju", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(5000)

    # 滚动到底部触发懒加载
    for _ in range(10):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(500)

    # 获取全文
    text = page.inner_text("body")
    browser.close()

# 解析 Q/A 对
lines = text.split("\n")
qa_pairs = []
current_q = None
for line in lines:
    line = line.strip()
    if line.startswith("Q：") or line.startswith("Q:"):
        if current_q:
            qa_pairs.append(current_q)
        current_q = {"question": line[2:].strip(), "answer": ""}
    elif (line.startswith("A：") or line.startswith("A:")) and current_q:
        current_q["answer"] = line[2:].strip()
        qa_pairs.append(current_q)
        current_q = None
    elif current_q and line and not line.startswith(("提示", "科举答题", "支持输入")):
        # 多行答案追加
        if current_q["answer"]:
            current_q["answer"] += line
        else:
            current_q["answer"] = line

if current_q and current_q["answer"]:
    qa_pairs.append(current_q)

print(f"解析到 {len(qa_pairs)} 道题")

# 读取现有题库
bank_path = os.path.join(ROOT, "banks", "keju", "questions.json")
existing = json.load(open(bank_path, encoding="utf-8-sig"))
existing_questions = {e["question"] for e in existing}
print(f"现有题库: {len(existing)} 题")

# 合并：新增不在现有题库中的题目
new_count = 0
next_id = max(int(e.get("id", 0)) for e in existing) + 1
for qa in qa_pairs:
    q_text = qa.get("question", "").strip()
    a_text = qa.get("answer", "").strip()
    if not q_text or not a_text:
        continue
    if q_text in existing_questions:
        continue
    existing.append({"id": str(next_id), "question": q_text, "options": [], "answer": a_text})
    existing_questions.add(q_text)
    next_id += 1
    new_count += 1

print(f"新增 {new_count} 题，合并后共 {len(existing)} 题")

# 写入
with open(bank_path, "w", encoding="utf-8") as f:
    json.dump(existing, f, ensure_ascii=False, indent=1)
print(f"题库已更新: {bank_path}")
