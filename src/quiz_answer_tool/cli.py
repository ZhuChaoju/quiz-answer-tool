"""命令行入口。"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from .matcher import QuestionBank
from .pipeline import Pipeline
from .window import find_window, list_windows

DEFAULT_CONFIG = "config.json"


def _load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def cmd_list_windows(_: argparse.Namespace) -> None:
    for hwnd, title in list_windows():
        print(f"{hwnd}\t{title}")


def cmd_calibrate(args: argparse.Namespace) -> None:
    import os

    from . import capture
    from .window import get_client_rect

    keyword = args.keyword
    hwnd = find_window(keyword) if keyword else None
    if hwnd is None:
        print("window not found, provide --keyword", file=sys.stderr)
        sys.exit(1)
    os.makedirs("captures", exist_ok=True)
    rect = get_client_rect(hwnd)
    print(f"client rect: {rect.left},{rect.top} {rect.right},{rect.bottom}")
    for name, region in (("question", args.question), ("options", args.options)):
        img = capture.capture_region(hwnd, region)
        path = f"captures/{name}.png"
        img.save(path)
        print(f"saved {path} ({img.size[0]}x{img.size[1]})")
    config = {
        "window_title_keyword": keyword,
        "hotkey": "f8",
        "interval_sec": 0.5,
        "region_question": args.question,
        "region_options": args.options,
        "ocr": {"lang": "ch", "confidence": 0.6},
    }
    with open(DEFAULT_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print(f"wrote {DEFAULT_CONFIG} (review the screenshots and adjust percentages)")


def cmd_run(args: argparse.Namespace) -> None:
    cfg = _load_config(args.config)
    hwnd = find_window(cfg.get("window_title_keyword", ""))
    if hwnd is None:
        print("target window not found", file=sys.stderr)
        sys.exit(1)
    bank = QuestionBank.load(args.questions)
    pipeline = Pipeline(cfg, dry_run=args.dry_run)
    pipeline.bank = bank
    print("press F8 to toggle, Ctrl+C to quit")
    try:
        pipeline.run(hwnd)
    except KeyboardInterrupt:
        pipeline.stop()
        print("\nstopped")


def main() -> None:
    parser = argparse.ArgumentParser(prog="quiz_answer_tool")
    parser.add_argument("--debug", action="store_true", help="enable debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-windows", help="list visible windows").set_defaults(func=cmd_list_windows)

    p_cal = sub.add_parser("calibrate", help="capture regions and write config.json")
    p_cal.add_argument("--keyword", default="", help="window title keyword")
    p_cal.add_argument("--question", default={"x": 10, "y": 60, "w": 80, "h": 20}, type=json.loads)
    p_cal.add_argument("--options", default={"x": 10, "y": 80, "w": 80, "h": 15}, type=json.loads)
    p_cal.set_defaults(func=cmd_calibrate)

    p_run = sub.add_parser("run", help="run the pipeline")
    p_run.add_argument("--config", default=DEFAULT_CONFIG)
    p_run.add_argument("--questions", default="questions.json")
    p_run.add_argument("--dry-run", action="store_true", help="OCR+match only, no clicks")
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    args.func(args)


if __name__ == "__main__":
    main()
