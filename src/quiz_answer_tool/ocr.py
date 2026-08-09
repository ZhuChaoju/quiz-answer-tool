"""RapidOCR 封装：按行返回识别文本（onnx 推理，比 Paddle 快 3-5 倍）。"""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
from PIL import Image

# OCR 常把换行/噪声误识成竖线类字符，识别后统一剔除（题目里实际不含此类字符）
VLINE_RE = re.compile(r"[|｜丨¦ǀ‖]")


@dataclass
class Line:
    text: str
    center_x: float
    center_y: float
    confidence: float
    width: float = 0.0
    height: float = 0.0
    # 行内各段（OCR 检测框）的文本与水平占比 (left, right)，用于精确圈选
    segments: tuple[tuple[str, float, float], ...] = ()


_ocr_engine = None
_ENGINE_FAILED = False


def _get_engine():
    """惰性加载 RapidOCR（默认中文模型）。"""
    global _ocr_engine, _ENGINE_FAILED
    if _ocr_engine is not None:
        return _ocr_engine
    if _ENGINE_FAILED:
        raise RuntimeError("RapidOCR 引擎初始化失败")
    try:
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError:
            from rapidocr import RapidOCR
        _ocr_engine = RapidOCR()
    except Exception as exc:
        _ENGINE_FAILED = True
        raise RuntimeError(f"RapidOCR 初始化失败: {exc}") from exc
    return _ocr_engine


def recognize(img: Image.Image, lang: str = "ch", min_confidence: float = 0.6) -> list[Line]:
    """识别图片中的文本，按行返回（同行文本自动合并，按纵向位置排序）。"""
    engine = _get_engine()
    result, _ = engine(np.asarray(img.convert("RGB")))
    lines: list[Line] = []
    for item in result or []:
        box, text, confidence = item
        if float(confidence) < min_confidence or not text.strip():
            continue
        text = VLINE_RE.sub("", str(text).strip())
        if not text:
            continue
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        lines.append(
            Line(
                text=str(text).strip(),
                center_x=sum(xs) / len(xs),
                center_y=sum(ys) / len(ys),
                confidence=float(confidence),
                width=max(xs) - min(xs),
                height=max(ys) - min(ys),
            )
        )
    return merge_lines(lines)


def merge_lines(lines: list[Line]) -> list[Line]:
    """把纵向相邻（同一文本行被 OCR 切成多段）的行合并，段内按横向排序。"""
    if not lines:
        return []
    ordered = sorted(lines, key=lambda ln: ln.center_y)
    groups: list[list[Line]] = []
    for ln in ordered:
        if groups and ln.center_y - groups[-1][-1].center_y < (
            max(ln.height, groups[-1][-1].height) * 0.9
        ):
            groups[-1].append(ln)
        else:
            groups.append([ln])
    merged: list[Line] = []
    for group in groups:
        group.sort(key=lambda ln: ln.center_x)
        total_w = sum(ln.width for ln in group)
        if total_w > 0:
            weights = sum(ln.center_x * ln.width for ln in group) / total_w
        else:  # 异常防护：所有段宽为 0 时退化为均值
            weights = sum(ln.center_x for ln in group) / len(group)
        # 段坐标：每个检测框在该行内的水平占比，供红框精确定位选项
        segments: list[tuple[str, float, float]] = []
        acc = 0.0
        for ln in group:
            left = acc / total_w if total_w > 0 else 0.0
            acc += ln.width
            right = acc / total_w if total_w > 0 else 1.0
            segments.append((ln.text, left, right))
        merged.append(
            Line(
                text="".join(ln.text for ln in group),
                center_x=weights,
                center_y=sum(ln.center_y for ln in group) / len(group),
                confidence=min(ln.confidence for ln in group),
                width=sum(ln.width for ln in group),
                segments=tuple(segments),
            )
        )
    return merged
