"""通用 HTML → 题库 JSON 转换器。

不绑定任何特定站点：题目块、题干、选项、答案的提取规则均由命令行参数指定，
默认按常见结构（.question 块内含 .title / .option / .answer）工作。

用法示例:
    python tools/html_to_json.py input.html -o questions.json
    python tools/html_to_json.py input.html -i ".item" -q ".q" -p "li" -a ".correct" -o out.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser


class _TextCollector(HTMLParser):
    """收集纯文本，忽略标签与脚本/样式内容。"""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in ("script", "style"):
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip and data.strip():
            self._parts.append(data.strip())

    def text(self) -> str:
        return " ".join(self._parts).strip()


def _text(html: str) -> str:
    p = _TextCollector()
    p.feed(html)
    return p.text()


def _parse_selector(selector: str) -> tuple[str, str]:
    """把 'tag' / '.class' / 'tag.class' 解析为 (tag, class)。"""
    if "." in selector:
        tag, _, cls = selector.partition(".")
        return tag, cls
    return selector, ""


def _split_blocks(html: str, selector: str) -> list[str]:
    """按选择器切分 HTML 为若干块。

    选择器支持 'tag'、'.class'、'tag.class'。按开标签匹配并计入层级的
    闭合标签计数，保证块边界准确。
    """
    tag_sel, class_sel = _parse_selector(selector)
    start_re = re.compile(
        r"<" + tag_sel + r"\b[^>]*class=(\"[^\"]*\"|'[^']*')[^>]*>", re.I
    ) if class_sel else re.compile(r"<" + tag_sel + r"\b[^>]*>", re.I)

    blocks: list[str] = []
    depth = 0
    start_pos: int | None = None
    for m in re.finditer(r"<(/?)(\w+)\b[^>]*>", html, re.I):
        token = m.group(0)
        if tag_sel and not m.group(2).lower() == tag_sel.lower():
            continue
        if m.group(1):  # closing
            depth -= 1
            if depth == 0 and start_pos is not None:
                blocks.append(html[start_pos:m.end()])
                start_pos = None
        else:  # opening
            sm = start_re.search(token)
            if class_sel:
                matched = bool(sm) and class_sel in sm.group(1).strip("\"'").split()
            else:
                matched = bool(sm)
            if matched:
                depth = 1
                start_pos = m.start()
            elif depth > 0:
                depth += 1
    return blocks


def _extract_fields(block: str, selectors: dict[str, str]) -> dict[str, list[str]]:
    """从题目块中按各字段选择器提取文本片段列表。"""
    result: dict[str, list[str]] = {}
    for field, selector in selectors.items():
        result[field] = [_text(b) for b in _split_blocks(block, selector) if _text(b)]
    return result


def extract_questions(
    html: str,
    item_selector: str,
    question_selector: str,
    options_selector: str,
    answer_selector: str,
) -> list[dict]:
    questions: list[dict] = []
    for idx, block in enumerate(_split_blocks(html, item_selector), start=1):
        fields = _extract_fields(
            block,
            {
                "question": question_selector,
                "options": options_selector,
                "answer": answer_selector,
            },
        )
        question = fields["question"][0] if fields["question"] else ""
        if not question:
            continue
        options = fields["options"]
        answer = fields["answer"][0] if fields["answer"] else ""
        if answer:
            answer = _answer_letter(answer, options)
        questions.append(
            {"id": idx, "question": question, "options": options, "answer": answer}
        )
    return questions


def _answer_letter(answer: str, options: list[str]) -> str:
    """把答案文本/前缀字母归一为选项字母（A/B/C/...），无法识别则原样返回。"""
    head = answer[:1].upper()
    if head in "ABCDEFGH":
        return head
    for i, opt in enumerate(options):
        if answer in opt:
            return "ABCDEFGH"[i]
    return answer


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert HTML quiz pages to JSON")
    parser.add_argument("input", help="input HTML file")
    parser.add_argument("-o", "--output", default="questions.json")
    parser.add_argument("-i", "--item", default=".question")
    parser.add_argument("-q", "--question", default=".title")
    parser.add_argument("-p", "--options", default=".option")
    parser.add_argument("-a", "--answer", default=".answer")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as f:
        html = f.read()
    questions = extract_questions(
        html, args.item, args.question, args.options, args.answer
    )
    if not questions:
        print("no questions extracted, check your selectors", file=sys.stderr)
        sys.exit(1)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    print(f"extracted {len(questions)} questions -> {args.output}")


if __name__ == "__main__":
    main()
