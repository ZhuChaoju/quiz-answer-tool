# -*- coding: utf-8 -*-
"""sqlite 题库(database.db: question 表) → questions.json（元宵节模块）。

用法:
    python tools/db_to_questions.py D:\\work\\_downloads\\database.db -o banks\\yuanxiao\\questions.json
"""

from __future__ import annotations

import argparse
import json
import sqlite3


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert sqlite question bank to questions.json")
    parser.add_argument("input", help="sqlite file with question(question, answer) table")
    parser.add_argument("-o", "--output", default="questions.json")
    args = parser.parse_args()

    conn = sqlite3.connect(args.input)
    rows = conn.execute("select question, answer from question").fetchall()
    questions = []
    seen = set()
    for q, a in rows:
        q = (q or "").strip()
        a = (a or "").strip()
        if not q or not a or q in seen:
            continue
        seen.add(q)
        questions.append(
            {"id": len(questions) + 1, "question": q, "options": [], "answer": a}
        )
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=1)
    print(f"converted {len(questions)} questions -> {args.output}")


if __name__ == "__main__":
    main()
