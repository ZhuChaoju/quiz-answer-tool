# -*- coding: utf-8 -*-
import ctypes
import io
import os
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
print("now:", time.strftime("%Y-%m-%d %H:%M:%S"))

# exe 版本时间
p = r"D:\work\quiz-answer-tool\dist\release\quiz-answer-tool.exe"
print("exe mtime:", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(p))))

# 模拟工具的日志写入（frozen 语义）
log_dir = os.path.dirname(p)  # 等价于 frozen 时的 dirname(sys.executable)
os.makedirs(os.path.join(log_dir, "logs"), exist_ok=True)
path = os.path.join(log_dir, "logs", time.strftime("识别日志-%Y%m%d.txt"))
with open(path, "a", encoding="utf-8") as f:
    f.write(time.strftime("%Y-%m-%d %H:%M:%S") + " | 写入测试\n")
print("test write ok ->", path)
