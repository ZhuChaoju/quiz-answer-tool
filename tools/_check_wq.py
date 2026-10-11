# -*- coding: utf-8 -*-
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from quiz_answer_tool.matcher import QuestionBank

bank = QuestionBank.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "banks", "keju", "questions.json"))
for kw in ("武器店", "冥想"):
    print(f"== 含「{kw}」的题 ==")
    for k, e in zip(bank._keys, bank._raw):
        if kw in e.get("question", ""):
            print(f"   {e['question']} → {e['answer']}")
