# -*- coding: utf-8 -*-
"""活动模块基类：识别区域(ROI)、识别结果、答案圈选的共享实现与模块装配约定。"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any

from PIL import Image

from ..ocr import Line

DEFAULT_ROI = {"x": 10.0, "y": 10.0, "w": 60.0, "h": 30.0}

# 选项行前缀（A、 B. 1、 等）——文字题与看图说话共用
PREFIX_RE = re.compile(r"^[A-Za-z一二三四五六七八九十百\d]+[、.．:：]\s*")


@dataclass
class Roi:
    """识别区域：占画面百分比坐标（自适应分辨率），pad 为外扩容错像素比例。"""

    x: float
    y: float
    w: float
    h: float

    @classmethod
    def from_json(cls, data: dict[str, Any] | None) -> "Roi":
        d = dict(DEFAULT_ROI)
        d.update(data or {})
        return cls(x=float(d["x"]), y=float(d["y"]), w=float(d["w"]), h=float(d["h"]))

    def to_json(self) -> dict[str, float]:
        return {"x": round(self.x, 3), "y": round(self.y, 3), "w": round(self.w, 3), "h": round(self.h, 3)}

    def crop(self, img: Image.Image, pad: float = 0.0) -> Image.Image:
        """按百分比裁剪；pad 为相对区域尺寸的外扩比例（容错，防布局微移漏识别）。"""
        left, top, right, bottom = self.rect_px(img.size, pad)
        return img.crop((int(left), int(top), int(right), int(bottom)))

    def rect_px(self, size: tuple[int, int], pad: float = 0.0) -> tuple[float, float, float, float]:
        """区域在整图中的像素矩形 (left, top, right, bottom)；int 舍入与 crop() 完全一致。"""
        w, h = size
        pw, ph = self.w * pad, self.h * pad
        left = max(0, int(w * (self.x - pw) / 100))
        top = max(0, int(h * (self.y - ph) / 100))
        right = min(w, left + int(w * (self.w + 2 * pw) / 100))
        bottom = min(h, top + int(h * (self.h + 2 * ph) / 100))
        return left, top, right, bottom


@dataclass
class ModuleResult:
    """一次识别的结果：题面、答案、答案在选项区内的定位行。"""

    question: str = ""
    answer: str = ""
    answer_line: tuple[Line, float, float] | None = None
    lines: list[Line] = field(default_factory=list)
    matched: dict | None = None  # 命中的题库条目/图标条目
    note: str = ""  # 额外提示（未命中等）
    state: str = "no_dialog"  # hit=命中 / miss_in_question=答题中未命中 / no_dialog=无题目
    # 选项区实际使用的整图像素矩形（图标模块跟随定位时与百分比 ROI 不同）
    option_rect: tuple[int, int, int, int] | None = None


class BaseModule:
    """活动模块基类：子类实现 recognize()，并给出各自 ROI 键位。"""

    type = "base"
    ROI_KEYS: tuple[str, ...] = ("question", "option")

    def __init__(self, mid: str, name: str, bank_dir: str, rois: dict[str, Roi] | None = None):
        self.id = mid
        self.name = name
        self.bank_dir = bank_dir
        self.rois: dict[str, Roi] = rois or {k: Roi.from_json(None) for k in self.ROI_KEYS}

    # ---- 装配 ----
    @classmethod
    def from_json(cls, data: dict[str, Any], bank_dir: str) -> "BaseModule":
        raise NotImplementedError

    def _base_init(self, data: dict[str, Any], bank_dir: str) -> None:
        self.id = str(data.get("id") or os.path.basename(bank_dir))
        self.name = str(data.get("name") or self.id)
        self.bank_dir = bank_dir
        roi_data = data.get("roi") or {}
        self.rois = {k: Roi.from_json(roi_data.get(k)) for k in self.ROI_KEYS}
        # OCR 行折行合并阈值（相对行高）；科举折行题面 0.6，可按模块配置覆盖
        self.merge_threshold = float(data.get("merge_threshold", 0.6))

    # ---- 识别（由识别线程调用，frame 为整幅截图） ----
    def recognize(self, frame: Image.Image) -> ModuleResult:
        raise NotImplementedError

    # ---- 配置持久化（ROI 校准后保存回模块 json） ----
    def config_path(self) -> str | None:
        return None

    def save_rois(self, extra: dict[str, Any] | None = None) -> str | None:
        """把当前 ROI 写回模块配置文件，返回写入路径；无配置文件时返回 None。"""
        path = self.config_path()
        if not path or not os.path.exists(path):
            return None
        import json

        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
        data["roi"] = {k: r.to_json() for k, r in self.rois.items()}
        if extra:
            data.update(extra)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return path


# ---- 答案圈选共享实现（文字题与看图说话的默认行为，子类可覆写） ----
def find_answer_line(
    lines: list[Line], answer: str
) -> tuple[Line, float, float] | None:
    """在选项识别行里定位答案行，返回 (行, 答案段绝对像素左右 x) 供红框圈选。

    命中策略：先按包含关系精确匹配；全部未中时按相似度兜底（≥70/100 才采用）。
    """
    from rapidfuzz import fuzz

    answer = answer.strip()
    if not answer:
        return None
    parts = [p.strip() for p in re.split(r"[/／]", answer) if p.strip()]

    def clean(text: str) -> str:
        return PREFIX_RE.sub("", text.strip())

    for ln in lines:
        text = clean(ln.text)
        if not text:
            continue
        for part in parts:
            if part == text or part in text or text in part:
                return ln, *segment_bounds(ln, part)
    best: Line | None = None
    best_ratio = 0
    for ln in lines:
        text = clean(ln.text)
        if not text:
            continue
        ratio = max(fuzz.ratio(part, text) for part in parts)  # 0~100
        if ratio > best_ratio:
            best, best_ratio = ln, ratio
    return (best, best.center_x - best.width / 2, best.center_x + best.width / 2) if best and best_ratio >= 70 else None


def segment_bounds(line: Line, part: str) -> tuple[float, float]:
    """定位答案所在 OCR 段的绝对像素范围（选项框之间有间隙，必须用绝对坐标）。"""
    if line.segments:
        n = len(line.segments)
        for seg_text, x1, x2 in line.segments:
            if part in seg_text or seg_text in part:
                return x1, x2
        best: tuple[float, float] | None = None
        for i in range(n):
            combined = line.segments[i][0]
            for j in range(i, n):
                if j > i:
                    combined += line.segments[j][0]
                if part in combined or combined in part:
                    span = (line.segments[i][1], line.segments[j][2])
                    if best is None or (span[1] - span[0]) < (best[1] - best[0]):
                        best = span
        if best is not None:
            return best
    idx = line.text.find(part)
    if idx >= 0:
        # 无段信息时退化为行内字符比例（单检测框场景，无间隙问题）
        w = line.width
        return line.center_x - w / 2 + w * idx / max(len(line.text), 1), \
            line.center_x - w / 2 + w * (idx + len(part)) / max(len(line.text), 1)
    return line.center_x - line.width / 2, line.center_x + line.width / 2
