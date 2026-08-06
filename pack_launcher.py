"""PyInstaller 打包入口：以模块方式启动，保证相对导入正常。

windowed 模式下 sys.stdout/stderr 为 None，print/logging 会崩溃，
这里统一重定向到日志文件，便于排查问题。
"""

import os
import sys


def _redirect_stdio() -> None:
    # frozen 模式下 __file__ 指向临时解压目录，日志写到 exe 所在目录（固定位置）
    base = os.path.dirname(os.path.abspath(sys.executable))
    if sys.stdout is None:
        sys.stdout = open(os.path.join(base, "stdout.log"), "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.path.join(base, "stderr.log"), "w", encoding="utf-8")


if getattr(sys, "frozen", False):
    _redirect_stdio()

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from quiz_answer_tool.cli import main

if __name__ == "__main__":
    main()
