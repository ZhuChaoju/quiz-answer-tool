"""命令行入口。"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

from .matcher import QuestionBank
from .viewer import Viewer

DEFAULT_CONFIG = "config.json"


def _enable_dpi_awareness() -> None:
    """Windows 高分屏：声明进程 DPI 感知，使窗口坐标与截图像素一致。

    必须在本进程创建任何窗口（Tk）之前调用；非 Windows 平台无操作。
    """
    if sys.platform != "win32":
        return
    import ctypes

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        ctypes.windll.user32.SetProcessDPIAware()


def _load_config(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(
            f"配置文件 {path} 不存在，使用默认配置；"
            f"可从 config/config.example.json 复制一份。",
            file=sys.stderr,
        )
        return {}


def _resolve_path(path: str) -> str:
    """解析数据文件路径：exe 场景优先 exe 目录，其次当前工作目录；源码场景用当前目录。"""
    if os.path.isabs(path):
        return path
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        if os.path.exists(os.path.join(exe_dir, path)):
            return os.path.join(exe_dir, path)
    return os.path.join(os.getcwd(), path)


def cmd_run(args: argparse.Namespace) -> None:
    args.config = _resolve_path(args.config)
    args.questions = _resolve_path(args.questions)
    cfg = _load_config(args.config)
    try:
        bank = QuestionBank.load(args.questions)
    except FileNotFoundError:
        print(
            f"题库文件 {args.questions} 不存在；"
            f"可用 tools/keju_to_questions.py 从题库文本生成。",
            file=sys.stderr,
        )
        bank = None
    app = Viewer(cfg, bank, bank_path=args.questions)
    app.mainloop()


def main() -> None:
    _enable_dpi_awareness()
    parser = argparse.ArgumentParser(prog="quiz_answer_tool")
    parser.add_argument("--debug", action="store_true", help="enable debug logging")
    sub = parser.add_subparsers(dest="command")

    p_run = sub.add_parser("run", help="open the live recognition window")
    p_run.add_argument("--config", default=DEFAULT_CONFIG)
    p_run.add_argument("--questions", default="questions.json")
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    if not args.command:  # 无子命令时默认 run（exe 双击场景）
        args.debug = False
        args.func = cmd_run
        args.config = DEFAULT_CONFIG
        args.questions = "questions.json"
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    args.func(args)


if __name__ == "__main__":
    main()
