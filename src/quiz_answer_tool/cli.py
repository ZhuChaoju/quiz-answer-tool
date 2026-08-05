"""命令行入口。"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from .matcher import QuestionBank
from .viewer import Viewer

DEFAULT_CONFIG = "config.json"


def _load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def cmd_run(args: argparse.Namespace) -> None:
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
    parser = argparse.ArgumentParser(prog="quiz_answer_tool")
    parser.add_argument("--debug", action="store_true", help="enable debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="open the live recognition window")
    p_run.add_argument("--config", default=DEFAULT_CONFIG)
    p_run.add_argument("--questions", default="questions.json")
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    args.func(args)


if __name__ == "__main__":
    main()
