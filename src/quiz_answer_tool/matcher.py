"""题库加载与三级匹配：精确 → 子串 → 模糊；图标库 dHash 汉明距离匹配(看图说话)。"""

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
        # utf-8-sig:兼容带 BOM 的题库文件(记事本保存常见)
        with open(path, encoding="utf-8-sig") as f:
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


class IconBank:
    """看图说话图标库：256 位图标哈希 → 答案，汉明距离匹配。

    未命中时由用户录入答案并连同当前图标哈希入库，越用越全。
    """

    def __init__(self, entries: list[dict[str, Any]], threshold: int = 12):
        self._entries = entries  # [{"hash": "64位hex", "answer": "龙吟"}, ...]
        self.threshold = threshold  # 256 位哈希:同图标渲染噪声 0~2,不同内容实测 ≥27

    @classmethod
    def load(cls, path: str) -> "IconBank":
        try:
            with open(path, encoding="utf-8-sig") as f:
                data = json.load(f)
        except FileNotFoundError:
            data = []
        return cls(data if isinstance(data, list) else [])

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._entries, f, ensure_ascii=False, indent=1)

    def __len__(self) -> int:
        return len(self._entries)

    @staticmethod
    def _dist(a: str, b: str) -> int:
        return bin(int(a, 16) ^ int(b, 16)).count("1")

    def match(self, icon_hash: str) -> str | None:
        """最近哈希距离 ≤ threshold 时返回其答案，否则 None。"""
        best: tuple[int, str] | None = None
        for e in self._entries:
            h = str(e.get("hash", ""))
            if not h:
                continue
            try:
                d = self._dist(icon_hash, h)
            except ValueError:
                continue
            if best is None or d < best[0]:
                best = (d, str(e.get("answer", "")))
        if best and best[0] <= self.threshold and best[1]:
            return best[1]
        return None

    def add(self, icon_hash: str, answer: str) -> None:
        """收录一条图标答案（同哈希已存在时更新答案）。"""
        for e in self._entries:
            if e.get("hash") == icon_hash:
                e["answer"] = answer
                return
        self._entries.append({"hash": icon_hash, "answer": answer})
