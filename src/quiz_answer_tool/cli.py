"""命令行入口。"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

from .activities import load_modules
from .viewer import Viewer

DEFAULT_CONFIG = "config.json"


def _enable_dpi_awareness() -> None:
    """Windows 高分屏：声明进程 DPI 感知，使窗口坐标与截图像素一致。

    必须在本进程创建任何窗口（Tk）之前调用；非 Windows 平台无操作。
    优先 Per-Monitor-V2：125%/150% 缩放下抓到的是原生分辨率画面（OCR 更清晰），
    失败再退回 shcore(1)、最后 SetProcessDPIAware。
    """
    if sys.platform != "win32":
        return
    import ctypes

    try:
        # Windows 10 1703+：Per-Monitor V2（-4 为 DPI_AWARENESS_CONTEXT 值）
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _load_config(path: str) -> dict:
    try:
        # utf-8-sig:兼容记事本/PowerShell 保存的带 BOM 配置(严格 utf-8 会解码失败)
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except FileNotFoundError:
        print(
            f"配置文件 {path} 不存在，使用默认配置；可从 config/config.example.json 复制一份。",
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
    cfg = _load_config(args.config)
    banks_dir = _resolve_path(args.banks)
    modules = load_modules(banks_dir)
    if not modules:
        print(
            f"在 {banks_dir} 未找到任何活动模块；请把 banks 目录与 exe 放在一起（或源码根目录运行）。",
            file=sys.stderr,
        )
        raise SystemExit(1)
    app = Viewer(cfg, modules, config_path=args.config)
    app.mainloop()


def main() -> None:
    _enable_dpi_awareness()
    parser = argparse.ArgumentParser(prog="quiz_answer_tool")
    parser.add_argument("--debug", action="store_true", help="enable debug logging")
    sub = parser.add_subparsers(dest="command")

    p_run = sub.add_parser("run", help="open the live recognition window")
    p_run.add_argument("--config", default=DEFAULT_CONFIG)
    p_run.add_argument("--banks", default="banks")
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    if not args.command:  # 无子命令时默认 run（exe 双击场景）
        args.debug = False
        args.func = cmd_run
        args.config = DEFAULT_CONFIG
        args.banks = "banks"
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    args.func(args)


if __name__ == "__main__":
    main()
