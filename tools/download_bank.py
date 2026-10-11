# -*- coding: utf-8 -*-
"""下载官方答题器题库并合并到本地 keju 题库。"""
import ast
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import requests

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# 下载
for url in ("https://w.163.com/h5/xyq/dtk/api/questions",
            "https://w.163.com/h5/xyq/dtk/data.json"):
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200 and len(r.text) > 100:
            print(f"下载成功: {url} ({len(r.text)} bytes)")
            data = r.json() if r.text.startswith(("{", "[")) else None
            if data:
                print(f"数据类型: {type(data).__name__}")
                if isinstance(data, list):
                    print(f"题目数: {len(data)}")
                    print("示例:", data[:2])
                elif isinstance(data, dict):
                    print(f"键: {list(data.keys())[:10]}")
            else:
                print("非JSON:", r.text[:200])
            break
    except Exception as e:
        print(f"{url} ERROR: {e}")
