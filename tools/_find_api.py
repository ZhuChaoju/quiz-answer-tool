# -*- coding: utf-8 -*-
import ast
import io
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import requests

UA = {"User-Agent": "Mozilla/5.0"}
base = "https://w.163.com"

# 下载 app.js 搜索 API 路径
r = requests.get(f"{base}/h5/xyq/dtk/static/js/app.82e45b63.js", headers=UA, timeout=15)
js = r.text
print(f"app.js: {len(js)} bytes")

# 搜索 API 端点模式
api_patterns = re.findall(r'(?:baseURL|apiUrl|api[_-]?url|get|post)\s*[:(]\s*["\']([^"\']*(?:api|question|keju|题)[^"\']*)["\']', js, re.I)
print("API patterns:", api_patterns[:10])

# 搜索所有 /api/ 或 /h5/ 路径
api_paths = re.findall(r'["\'](/(?:api|h5)[^"\']{3,60})["\']', js)
print("URL paths:", list(set(api_paths))[:20])

# 搜索 .json 文件引用
json_refs = re.findall(r'["\']([^"\']*\.json)["\']', js)
print("JSON refs:", json_refs[:10])

# 搜索题目相关变量名
var_names = re.findall(r'(questionList|questionArr|tkList|题目|daan|答案)', js)
print("question vars:", list(set(var_names))[:10])
