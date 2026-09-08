"""跨平台截屏源：Windows 支持窗口与全屏，其他平台支持全屏。"""

from __future__ import annotations

import threading
from dataclasses import dataclass

import mss
from PIL import Image

_local = threading.local()


def _mss() -> mss.mss:
    """mss 实例线程内复用：每次新建都要重新分配 GDI 资源，是高频截图卡顿的主因。"""
    sct = getattr(_local, "sct", None)
    if sct is None:
        sct = mss.mss()
        _local.sct = sct
    return sct


@dataclass
class Source:
    id: str
    name: str
    kind: str  # "window" | "monitor"


@dataclass
class ScreenRect:
    left: int
    top: int
    width: int
    height: int


def list_sources() -> list[Source]:
    sources: list[Source] = []
    with mss.mss() as sct:
        for i, mon in enumerate(sct.monitors):
            label = "全部屏幕" if i == 0 else f"屏幕 {i}"
            sources.append(Source(id=f"monitor:{i}", name=label, kind="monitor"))
    try:
        import win32gui  # type: ignore

        def _callback(hwnd: int, _: object) -> bool:
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                sources.append(
                    Source(id=f"window:{hwnd}", name=win32gui.GetWindowText(hwnd), kind="window")
                )
            return True

        win32gui.EnumWindows(_callback, None)
    except ImportError:
        pass
    return sources


def capture(source: Source) -> tuple[Image.Image, ScreenRect]:
    """抓取来源画面，返回 (PIL.Image, 原始屏幕坐标矩形)。"""
    sct = _mss()
    if source.kind == "monitor":
        mon = sct.monitors[int(source.id.split(":")[1])]
        box = {"left": mon["left"], "top": mon["top"], "width": mon["width"], "height": mon["height"]}
        rect = ScreenRect(box["left"], box["top"], box["width"], box["height"])
    else:
        import win32gui  # type: ignore

        hwnd = int(source.id.split(":")[1])
        x, y, right, bottom = win32gui.GetWindowRect(hwnd)
        rect = ScreenRect(x, y, right - x, bottom - y)
        box = {"left": x, "top": y, "width": rect.width, "height": rect.height}
    shot = sct.grab(box)
    img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
    return img, rect


def crop_region(img: Image.Image, region: dict) -> Image.Image:
    """按百分比区域 {x,y,w,h} 截取图像。"""
    w, h = img.size
    left = int(w * region["x"] / 100)
    top = int(h * region["y"] / 100)
    right = left + int(w * region["w"] / 100)
    bottom = top + int(h * region["h"] / 100)
    return img.crop((left, top, right, bottom))
