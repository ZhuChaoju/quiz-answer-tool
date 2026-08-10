"""RapidOCR 封装（PP-OCRv6）：按行返回识别文本。

模型档位（config 的 ocr.model_type 可配）：
- tiny  最快，精度略低
- small 默认，速度/精度均衡（与 C# 版一致）
- medium 精度最高，速度较慢（约 1.5s+，需自行评估）
"""

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
_MODEL_TYPE: str | None = None

_MODEL_TYPES = {"tiny", "small", "medium"}


def _get_engine(model_type: str = "small"):
    """惰性加载 RapidOCR（PP-OCRv6，onnxruntime 推理）。"""
    global _ocr_engine, _ENGINE_FAILED, _MODEL_TYPE
    if model_type not in _MODEL_TYPES:
        model_type = "small"
    if _ocr_engine is not None and _MODEL_TYPE == model_type:
        return _ocr_engine
    if _ENGINE_FAILED:
        raise RuntimeError("RapidOCR 引擎初始化失败")
    try:
        from rapidocr import EngineType, LangDet, LangRec, ModelType, OCRVersion, RapidOCR

        mt = {
            "tiny": ModelType.TINY,
            "small": ModelType.SMALL,
            "medium": ModelType.MEDIUM,
        }[model_type]
        _ocr_engine = RapidOCR(
            params={
                "Det.engine_type": EngineType.ONNXRUNTIME,
                "Det.lang_type": LangDet.CH,
                "Det.model_type": mt,
                "Det.ocr_version": OCRVersion.PPOCRV6,
                "Rec.engine_type": EngineType.ONNXRUNTIME,
                "Rec.lang_type": LangRec.CH,
                "Rec.model_type": mt,
                "Rec.ocr_version": OCRVersion.PPOCRV6,
            }
        )
        _MODEL_TYPE = model_type
    except ImportError as exc:
        _ENGINE_FAILED = True
        raise RuntimeError(f"缺少依赖: {exc}，请安装 rapidocr 与 onnxruntime") from exc
    except Exception as exc:
        _ENGINE_FAILED = True
        raise RuntimeError(f"RapidOCR 初始化失败: {exc}") from exc
    return _ocr_engine


def recognize(
    img: Image.Image,
    lang: str = "ch",
    min_confidence: float = 0.6,
    model_type: str = "small",
) -> list[Line]:
    """识别图片中的文本，按行返回（同行文本自动合并，按纵向位置排序）。"""
    engine = _get_engine(model_type)
    result = engine(np.asarray(img.convert("RGB")))
    lines: list[Line] = []
    if result.txts:
        for text, score, box in zip(result.txts, result.scores, result.boxes):
            if float(score) < min_confidence:
                continue
            text = VLINE_RE.sub("", str(text).strip())
            if not text:
                continue
            xs = box[:, 0]
            ys = box[:, 1]
            lines.append(
                Line(
                    text=text,
                    center_x=float(xs.mean()),
                    center_y=float(ys.mean()),
                    confidence=float(score),
                    width=float(xs.max() - xs.min()),
                    height=float(ys.max() - ys.min()),
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
                height=max(ln.height for ln in group),
                segments=tuple(segments),
            )
        )
    return merged
