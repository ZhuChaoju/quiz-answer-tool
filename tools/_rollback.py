# -*- coding: utf-8 -*-
import subprocess
import sys

r = subprocess.run(["git", "checkout", "47d31cd", "--", "src", "tools", "build_exe.bat"],
                   cwd=r"D:\work\quiz-answer-tool", capture_output=True, text=True)
print(r.stdout, r.stderr)
if r.returncode:
    sys.exit(r.returncode)
print("source reverted to 47d31cd state")
