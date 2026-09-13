# -*- coding: utf-8 -*-
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from quiz_answer_tool.matcher import QuestionBank

bank = QuestionBank.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "banks", "keju", "questions.json"))
q = "和好友共同战斗一场，好友度加多少"
hit = bank.match(q)
print("匹配到:", hit)
# 全库模糊搜相似题
from quiz_answer_tool.matcher import normalize
nq = normalize(q)
for k, e in zip(bank._keys, bank._raw):
    nk = normalize(e.get("question", ""))
    if "好友" in nk and ("战斗" in nk or "切磋" in nk):
        print("库内相关题:", e.get("question"), "->", e.get("answer"))
