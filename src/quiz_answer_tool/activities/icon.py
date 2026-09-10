# -*- coding: utf-8 -*-
"""看图说话模块（教师节活动）：题面是一枚技能/法术图标。

题库即素材库：banks/teachers/icons/ 存放官网（xyq.163.com，网易官方 CDN）
技能图标，icons.json 为构建好的 256 位梯度哈希 → 技能名索引。

识别管线（与构建 icons.json 完全同一套预处理）：
  1. 在搜索窗内用连通域自动定位图标方块（40x40 实心块，抗对话框挪动）；
  2. 边框中位色补方 → 64x64 → 内缩 12% 去浮雕边框 → 亮度图 → 17x16 梯度哈希；
  3. OCR 选项区得到候选技能名，逐个查库比距离（选项名过滤，175dt 同思路）；
  4. 选项都查不到时退回全库最近邻；仍超阈值则提示录入，越用越全。
"""

from __future__ import annotations

import json
import os
from collections import deque
from typing import Any

import numpy as np
from PIL import Image

from .. import ocr
from .base import PREFIX_RE, BaseModule, ModuleResult, find_answer_line  # noqa: F401  (re-export)

DEFAULT_THRESHOLD = 84  # 哈希距离阈值：真值实测 24~87，非同图标 ≥88
GLOBAL_THRESHOLD = 60  # 全库兜底路径的更严阈值（无选项过滤时防误命中）
S = 64  # 归一化尺寸
INSET = int(S * 0.12)  # 内缩比例：去掉游戏内浮雕边框/素材自带描边

_PREFIX_CHARS = "，。：：、（）()?？!!.． "


def _prep_64(img: Image.Image, bg: tuple[int, ...] | None = None) -> Image.Image:
    """边框中位色补方 → 64x64。素材侧 bg 传入合成底色，实况侧自动取边框中位色。"""
    if bg is None:
        lv = np.asarray(img.convert("RGB").resize((S, S), Image.BILINEAR), dtype=np.float64)
        border = np.concatenate([lv[0, :], lv[-1, :], lv[:, 0], lv[:, -1]])
        bg = tuple(int(c) for c in np.median(border, axis=0))
    w, h = img.size
    side = max(w, h)
    canvas = Image.new("RGB", (side, side), tuple(bg))
    rgba = img.convert("RGBA")
    canvas.paste(rgba, ((side - w) // 2, (side - h) // 2), rgba)
    return canvas.resize((S, S), Image.BILINEAR)


def lum_inset(img64: Image.Image) -> np.ndarray:
    """64x64 → 内缩 12% 的亮度图（去浮雕边框后比较图案本体）。"""
    a = np.asarray(img64, dtype=np.float64)
    lum = a[:, :, 0] * 0.299 + a[:, :, 1] * 0.587 + a[:, :, 2] * 0.114
    return lum[INSET:S - INSET, INSET:S - INSET]


def icon_hash(img: Image.Image, bg: tuple[int, ...] | None = None) -> str:
    """256 位横向梯度哈希（17x16）。实况裁剪与官网素材通用。"""
    g = Image.fromarray(np.clip(lum_inset(_prep_64(img, bg)), 0, 255).astype(np.uint8))
    g = g.resize((17, 16), Image.BILINEAR)
    px = list(g.getdata())
    bits = 0
    for y in range(16):
        row = y * 17
        for x in range(16):
            bits = (bits << 1) | int(px[row + x] < px[row + x + 1])
    return f"{bits:064x}"


def hamming(a: str, b: str) -> int:
    try:
        return bin(int(a, 16) ^ int(b, 16)).count("1")
    except ValueError:
        return 1 << 30


def _best_component(mask: np.ndarray, min_px: int, size_lo: int, size_hi: int):
    """在二值掩码里找最优连通域（填充率×方正度），返回局部像素 bbox 或 None。"""
    from collections import deque

    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    best: tuple[float, int, int, int, int] | None = None
    for sy in range(h):
        for sx in range(w):
            if not mask[sy, sx] or seen[sy, sx]:
                continue
            q = deque([(sy, sx)])
            seen[sy, sx] = True
            n = 0
            min_y = max_y = sy
            min_x = max_x = sx
            while q:
                y, x = q.popleft()
                n += 1
                min_y, max_y = min(min_y, y), max(max_y, y)
                min_x, max_x = min(min_x, x), max(max_x, x)
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        q.append((ny, nx))
            if n < min_px:
                continue
            bw, bh = max_x - min_x + 1, max_y - min_y + 1
            if not (size_lo <= bw <= size_hi and size_lo <= bh <= size_hi):
                continue
            fill = n / (bw * bh)
            square = 1.0 - abs(bw - bh) / max(bw, bh)
            score = fill * 0.6 + square * 0.4
            if best is None or score > best[0]:
                best = (score, min_x, min_y, max_x + 1, max_y + 1)
    return None if best is None else best[1:]


def _foreground_mask(img: Image.Image, search: dict, panel_bg, tol: float):
    """搜索窗内的前景掩码（与面板底色差异超容差）。"""
    w, h = img.size
    x0 = int(w * search["x"] / 100)
    y0 = int(h * search["y"] / 100)
    x1 = min(w, x0 + int(w * search["w"] / 100))
    y1 = min(h, y0 + int(h * search["h"] / 100))
    region = np.asarray(img.crop((x0, y0, x1, y1)).convert("RGB"), dtype=np.float64)
    mask = np.abs(region - np.array(panel_bg, dtype=np.float64)).sum(axis=2) > tol * 3
    return mask, (x0, y0, x1, y1)


def locate_icon(img: Image.Image, search: dict, panel_bg, tol: float = 28.0):
    """在百分比搜索窗内连通域定位图标方块，返回全图像素 bbox 或 None。

    图标=紧致实心块（30~55px 见方、填充率高）；问字徽标、文字等同为小块或
    不够方正，按 (填充率×方正度) 择优。对话框被拖动后仍能锁住图标。
    实现：先 2 倍降采样粗定位（4 倍像素量），再回原分辨率小窗精修 bbox。
    """
    mask, (x0, y0, x1, y1) = _foreground_mask(img, search, panel_bg, tol)
    small = mask[::2, ::2]
    cand = _best_component(small, min_px=100, size_lo=15, size_hi=27)
    if cand is None:
        return None
    # 回原分辨率：候选框映射 ×2 并外扩 4px，小窗内精修
    sx, sy, ex, ey = cand
    fx0 = max(0, x0 + sx * 2 - 4)
    fy0 = max(0, y0 + sy * 2 - 4)
    fx1 = min(x1, x0 + ex * 2 + 4)
    fy1 = min(y1, y0 + ey * 2 + 4)
    sub = np.asarray(img.crop((fx0, fy0, fx1, fy1)).convert("RGB"), dtype=np.float64)
    m2 = np.abs(sub - np.array(panel_bg, dtype=np.float64)).sum(axis=2) > tol * 3
    cand2 = _best_component(m2, min_px=400, size_lo=30, size_hi=55)
    if cand2 is None:
        return None
    a, b, c, d = cand2
    return (fx0 + a, fy0 + b, fx0 + c, fy0 + d)


class IconBank:
    """图标库：name/hash 条目 + 名称索引 + 最近邻查询。"""

    def __init__(self, entries: list[dict[str, Any]], threshold: int = DEFAULT_THRESHOLD):
        self._entries = entries
        self._by_name: dict[str, str] = {}
        self._table: list[tuple[str, str, int]] = []
        self.threshold = threshold
        for e in entries:
            name = str(e.get("name", "")).strip()
            h = str(e.get("hash", ""))
            if not name or not h:
                continue
            self._by_name.setdefault(name, h)
            self._table.append((name, h, int(h, 16)))

    @classmethod
    def load(cls, path: str, threshold: int = DEFAULT_THRESHOLD) -> "IconBank":
        try:
            with open(path, encoding="utf-8-sig") as f:
                data = json.load(f)
        except FileNotFoundError:
            data = []
        return cls(data if isinstance(data, list) else [], threshold)

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._entries, f, ensure_ascii=False, indent=0)

    def __len__(self) -> int:
        return len(self._entries)

    def hash_of(self, name: str) -> str | None:
        return self._by_name.get(name)

    def fuzzy_name(self, text: str) -> str | None:
        """OCR 出的选项名可能带错别字，模糊对回库名。"""
        from rapidfuzz import process, fuzz

        if not self._by_name:
            return None
        hit = process.extractOne(text, list(self._by_name), scorer=fuzz.ratio, score_cutoff=80)
        return hit[0] if hit else None

    def nearest(self, h: str) -> tuple[str, int] | None:
        """全库最近邻 (名称, 距离)。"""
        hi = int(h, 16)
        best: tuple[int, str] | None = None
        for name, _, hi2 in self._table:
            d = bin(hi ^ hi2).count("1")
            if best is None or d < best[0]:
                best = (d, name)
        return (best[1], best[0]) if best else None

    def add(self, h: str, name: str) -> None:
        if name in self._by_name:
            for e in self._entries:
                if e.get("name") == name:
                    e["hash"] = h
                    break
        else:
            self._entries.append({"name": name, "hash": h})
        self._by_name[name] = h
        self._table.append((name, h, int(h, 16)))


def option_candidates(o_lines: list[ocr.Line]) -> list[tuple[str, ocr.Line, float, float]]:
    """从选项区 OCR 行提取候选技能名：(名字, 所在行, 行内左右占比)。"""
    out: list[tuple[str, ocr.Line, float, float]] = []
    for ln in o_lines:
        if ln.segments:
            for seg_text, left, right in ln.segments:
                name = PREFIX_RE.sub("", seg_text).strip(_PREFIX_CHARS)
                if len(name) >= 2:
                    out.append((name, ln, left, right))
        else:
            name = PREFIX_RE.sub("", ln.text).strip(_PREFIX_CHARS)
            if len(name) >= 2:
                out.append((name, ln, 0.0, 1.0))
    return out


class IconModule(BaseModule):
    type = "icon"
    ROI_KEYS = ("icon", "option", "search")

    # 校准基准：图标 40px 见方；选项区相对图标左上角的像素偏移
    ICON_REF = 40
    OPTION_OFFSET_DEFAULT = (-19, 102, 376, 226)

    def __init__(self) -> None:
        self.bank: IconBank | None = None
        self.panel_bg = (162, 168, 210)
        self.last_hash: str | None = None  # 未命中录入时使用
        self.last_box: tuple[int, int, int, int] | None = None
        self.option_offset = self.OPTION_OFFSET_DEFAULT
        self.option_max_distance = DEFAULT_THRESHOLD

    @classmethod
    def from_json(cls, data: dict[str, Any], bank_dir: str) -> "IconModule":
        mod = cls()
        mod._base_init(data, bank_dir)
        bg = data.get("panel_bg")
        if isinstance(bg, list) and len(bg) == 3:
            mod.panel_bg = tuple(int(v) for v in bg)
        mod.option_offset = tuple(data.get("option_offset", mod.OPTION_OFFSET_DEFAULT))
        # 选项过滤路径的接受距离：答案必在四选项之一，且需对次优拉开 ≥4 边距，
        # 因此可比"无过滤"的全库阈值更宽（实测真值最高 87）
        mod.option_max_distance = int(data.get("option_max_distance", 100))
        threshold = int(data.get("threshold", DEFAULT_THRESHOLD))
        mod.bank = IconBank.load(os.path.join(bank_dir, data.get("icon_bank", "icons.json")), threshold)
        mod._config_path = os.path.join(bank_dir, "module.json")
        return mod

    def config_path(self) -> str | None:
        return getattr(self, "_config_path", None)

    def _option_rect_follow(self, frame: Image.Image, box: tuple[int, int, int, int]):
        """答题框被拖动后，选项区跟随图标：按图标实际位置+固定偏移换算。"""
        l, t, r, b = box
        s = (r - l) / self.ICON_REF
        dx1, dy1, dx2, dy2 = self.option_offset
        fw, fh = frame.size
        x1 = min(max(l + dx1 * s, 0), fw - 1)
        y1 = min(max(t + dy1 * s, 0), fh - 1)
        x2 = min(max(l + dx2 * s, x1 + 2), fw)
        y2 = min(max(t + dy2 * s, y1 + 2), fh)
        return (int(x1), int(y1), int(x2), int(y2))

    # ---- 识别 ----
    def recognize(self, frame: Image.Image, ocr_cfg: dict[str, Any]) -> ModuleResult:
        res = ModuleResult()
        roi_icon, roi_o, roi_s = self.rois["icon"], self.rois["option"], self.rois["search"]
        # 1) 图标定位：连通域优先（抗对话框拖动），失败退回固定 ROI
        box = locate_icon(frame, roi_s.__dict__, self.panel_bg) if roi_s.w > 0 else None
        if box:
            self.last_box = box
            icon_crop = frame.crop(box)
        else:
            self.last_box = None
            icon_crop = roi_icon.crop(frame)
        # 2) 选项区：图标定位成功时按固定偏移跟随（整框拖动场景）；否则退回百分比 ROI
        if box:
            orect = self._option_rect_follow(frame, box)
            res.option_rect = orect
            o_crop = frame.crop(orect)
        else:
            orect = roi_o.rect_px(frame.size, 0.02)
            res.option_rect = tuple(int(v) for v in orect)
            o_crop = frame.crop((int(orect[0]), int(orect[1]), int(orect[2]), int(orect[3])))
        mt = ocr_cfg.get("model_type", "tiny")
        lang = ocr_cfg.get("lang", "ch")
        conf = float(ocr_cfg.get("confidence", 0.4))
        dml = bool(ocr_cfg.get("use_dml", False))
        o_lines = ocr.recognize(o_crop, lang, conf, mt, True, dml, self.merge_threshold)
        res.lines = o_lines
        h = icon_hash(icon_crop)
        self.last_hash = h
        cands = option_candidates(o_lines)
        # 3) 选项名过滤匹配：最优选项 = 库内距离最小的那个候选
        scored: list[tuple[int, str, ocr.Line, float, float]] = []
        for name, ln, left, right in cands:
            lib_h = self.bank.hash_of(name) if self.bank else None
            if lib_h is None and self.bank:
                fname = self.bank.fuzzy_name(name)
                lib_h = self.bank.hash_of(fname) if fname else None
            if lib_h is None:
                continue
            scored.append((hamming(h, lib_h), name, ln, left, right))
        if scored and self.bank:
            scored.sort(key=lambda t: t[0])
            best = scored[0]
            # 与次优选项拉开 4 以上距离才算稳（防两个候选都贴近时的误选）
            margin_ok = len(scored) < 2 or scored[1][0] - best[0] >= 4
            if best[0] <= self.option_max_distance and margin_ok:
                res.answer = best[1]
                res.question = f"看图识别：{best[1]}"
                res.note = f"图标匹配距离 {best[0]}（选项过滤）"
                res.answer_line = (best[2], best[3], best[4])
                return res
        # 4) 全库兜底
        near = self.bank.nearest(h) if self.bank else None
        if near and near[1] <= GLOBAL_THRESHOLD:
            res.answer = near[0]
            res.question = f"看图识别：{near[0]}"
            res.note = f"全库匹配距离 {near[1]}"
            if res.answer_line is None and o_lines:
                res.answer_line = find_answer_line(o_lines, near[0])
            return res
        res.question = "图标未收录"
        res.note = f"图标未收录（最近: {near[0]} 距离{near[1]}），请在录入框输入技能名"
        return res
