"""题库加载与三级匹配：精确 → 子串 → 模糊。"""

from __future__ import annotations

import json
import re
from typing import Any

from rapidfuzz import fuzz, process

FULLWIDTH = str.maketrans(
    "０１２３４５６７８９ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ（）：，。！？",
    "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ():,。!?",
)


def normalize(text: str) -> str:
    """归一化：全半角转换、去空白与标点。"""
    text = text.translate(FULLWIDTH)
    text = re.sub(r"[\s\W_]+", "", text)
    return text.lower()


class QuestionBank:
    def __init__(self, questions: list[dict[str, Any]]):
        self._raw = questions
        self._index: list[tuple[str, dict]] = [
            (normalize(q.get("question", "")), q) for q in questions
        ]
        self._keys = [k for k, _ in self._index]

    @classmethod
    def load(cls, path: str) -> "QuestionBank":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls(data)

    def add(self, question: str, answer: str) -> None:
        """运行时收录一条题目答案（题目已存在时用新答案覆盖旧答案）。"""
        key = normalize(question)
        for normalized, q in self._index:
            if normalized == key:
                q["answer"] = answer
                return
        q = {"id": len(self._raw) + 1, "question": question, "options": [], "answer": answer}
        self._raw.append(q)
        self._index.append((key, q))
        self._keys.append(key)

    def __len__(self) -> int:
        return len(self._raw)

    def match(self, text: str) -> dict | None:
        """三级匹配，命中返回题目 dict，未命中返回 None。"""
        key = normalize(text)
        if not key:
            return None
        for normalized, q in self._index:
            if normalized == key:
                return q
        for normalized, q in self._index:
            if normalized in key or key in normalized:
                return q
        # rapidfuzz（C++ 实现）：全库模糊扫描比 difflib 快两个数量级
        hit = process.extractOne(key, self._keys, scorer=fuzz.ratio, score_cutoff=85)
        if hit is not None:
            return self._index[hit[2]][1]
        return None
