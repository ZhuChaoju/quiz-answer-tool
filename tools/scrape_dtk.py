# -*- coding: utf-8 -*-
"""用 requests 抓取官方答题器题库（尝试多种 API 路径和数据格式）。"""
import ast
import io
import json
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import requests

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://w.163.com/h5/xyq/dtk/index.html",
    "Origin": "https://w.163.com",
}

base = "https://w.163.com"

# 1) 下载主 JS 文件（真正的业务逻辑包）
js_candidates = []
html = requests.get(f"{base}/h5/xyq/dtk/index.html", headers=UA, timeout=15).text
js_files = re.findall(r'src="([^"]*\.js[^"]*)"', html)
for jf in js_files:
    full = jf if jf.startswith("http") else f"{base}/{jf.lstrip('/')}"
    try:
        r = requests.get(full, headers=UA, timeout=15)
        if len(r.text) > 10000:  # 大文件才可能是业务包
            js_candidates.append((full, r.text))
            print(f"JS: {full.split('/')[-1]} {len(r.text)}B")
    except Exception:
        pass

# 2) 在 JS 里搜索 API 端点
for js_name, js_text in js_candidates:
    # 常见模式
    for pattern in [
        r'["\'](?:https?:\/\/[^"\']*|)((?:\/(?:api|h5)[^"\']{5,80}))["\']',
        r'["\']((?:https?:\/\/)?[^"\']*(?:question|keju|topic|题)[^"\']{0,60})["\']',
        r'(?:get|post|axios)[\s(]+["\']([^"\']{5,80})["\']',
    ]:
        matches = re.findall(pattern, js_text)
        for m in matches:
            print(f"  API: {m}")

# 3) 搜索嵌入的题目数据
for js_name, js_text in js_candidates:
    # 找 JSON 数组中含 "question" 或 "题目" 的
    for m in re.finditer(r'\{[^{}]*"(?:q|question|title|stem)"[^{}]*\}', js_text):
        frag = m.group()
        if len(frag) > 50:
            print(f"  DATA: {frag[:200]}")
            break
