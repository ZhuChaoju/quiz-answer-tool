"""题库加载与三级匹配：精确 → 子串 → 模糊。"""

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from typing import Any

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

    @classmethod
    def load(cls, path: str) -> "QuestionBank":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls(data)

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
        best, best_ratio = None, 0.0
        for normalized, q in self._index:
            ratio = SequenceMatcher(None, key, normalized).ratio()
            if ratio > best_ratio:
                best, best_ratio = q, ratio
        if best and best_ratio >= 0.85:
            return best
        return None
