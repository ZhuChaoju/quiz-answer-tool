"""把题库文本（{Id, Q, A} 数组）转换为 pipeline 可读的 questions.json。

用法:
    python tools/keju_to_questions.py keju_tiku.txt -o questions.json
"""

from __future__ import annotations

import argparse
import json
import sys


def convert(data: list[dict]) -> list[dict]:
    questions = []
    seen: set[str] = set()
    for idx, item in enumerate(data, start=1):
        q = item.get("Q") or item.get("question") or ""
        a = item.get("A") or item.get("answer") or ""
        if not q or not a:
            continue
        if q in seen:
            continue
        seen.add(q)
        questions.append(
            {"id": item.get("Id") or idx, "question": q, "options": [], "answer": a}
        )
    return questions


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert question bank text to questions.json")
    parser.add_argument("input", help="input bank file (JSON array of {Id,Q,A})")
    parser.add_argument("-o", "--output", default="questions.json")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        print("input must be a JSON array", file=sys.stderr)
        sys.exit(1)
    questions = convert(data)
    if not questions:
        print("no questions converted", file=sys.stderr)
        sys.exit(1)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=1)
    print(f"converted {len(questions)} questions -> {args.output}")


if __name__ == "__main__":
    main()
