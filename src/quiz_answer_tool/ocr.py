"""PaddleOCR 封装：按行返回识别文本。"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image


@dataclass
class Line:
    text: str
    center_x: float
    center_y: float
    confidence: float


_ocr_engine = None


def _get_engine(lang: str = "ch"):
    global _ocr_engine
    if _ocr_engine is None:
        from paddleocr import PaddleOCR

        _ocr_engine = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)
    return _ocr_engine


def recognize(img: Image.Image, lang: str = "ch", min_confidence: float = 0.6) -> list[Line]:
    """识别图片中的文本，按行返回（按纵向位置排序）。"""
    engine = _get_engine(lang)
    result = engine.ocr(img.convert("RGB"))
    lines: list[Line] = []
    for page in result or []:
        for item in page or []:
            box, (text, confidence) = item
            if confidence < min_confidence or not text.strip():
                continue
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            lines.append(
                Line(
                    text=text.strip(),
                    center_x=sum(xs) / len(xs),
                    center_y=sum(ys) / len(ys),
                    confidence=float(confidence),
                )
            )
    lines.sort(key=lambda ln: ln.center_y)
    return lines
