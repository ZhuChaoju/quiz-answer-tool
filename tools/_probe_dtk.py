# -*- coding: utf-8 -*-
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import requests
import re

urls = [
    "https://w.163.com/h5/xyq/dtk/index.html",
    "https://w.163.com/h5/xyq/dtk/api/questions",
    "https://w.163.com/h5/xyq/dtk/data.json",
]
for u in urls:
    try:
        r = requests.get(u, timeout=10)
        print(f"{r.status_code} {len(r.text)} {u}")
        if r.status_code == 200 and len(r.text) > 100:
            # 找 JS/JSON 数据链接
            for m in re.findall(r'(https?://[^\s"\']+\.json|/api/[^\s"\']+|dataSrc[^\n]{0,80})', r.text[:3000]):
                print("  found:", m[:80])
    except Exception as e:
        print(f"{u} ERROR: {e}")
