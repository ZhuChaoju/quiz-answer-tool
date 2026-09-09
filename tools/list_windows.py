# -*- coding: utf-8 -*-
import io
import sys

sys.path.insert(0, r"D:\work\quiz-answer-tool\src")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from quiz_answer_tool import screen

for s in screen.list_sources():
    print(repr(s.name), s.kind, s.id)
