# -*- coding: utf-8 -*-
import subprocess
import sys

r = subprocess.run([sys.executable, "-X", "utf8", r"tools\test_text_modules.py"],
                   cwd=r"D:\work\quiz-answer-tool", capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
out = r.stdout + r.stderr
open(r"D:\work\_downloads\test_out.txt", "w", encoding="utf-8").write(out)
tail = [l for l in out.splitlines() if l.strip() and "RapidOCR" not in l and "onnx" not in l]
print("\n".join(tail[-12:]))
