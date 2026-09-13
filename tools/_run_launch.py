# -*- coding: utf-8 -*-
import subprocess
import sys

r = subprocess.run([sys.executable, r"tools\launch_latest.py"], cwd=r"D:\work\quiz-answer-tool",
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
print(r.stdout[-1200:])
if r.returncode != 0:
    print("STDERR:", r.stderr[-500:])
    sys.exit(1)
