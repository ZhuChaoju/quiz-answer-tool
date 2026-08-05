"""按窗口客户区百分比坐标截图。"""

from __future__ import annotations

import mss
from PIL import Image

from .window import get_client_rect


def region_to_pixels(client_rect, region: dict) -> dict:
    """百分比区域转像素区域（clip 到客户区边界）。"""
    w = client_rect.right - client_rect.left
    h = client_rect.bottom - client_rect.top
    left = client_rect.left + int(w * region["x"] / 100)
    top = client_rect.top + int(h * region["y"] / 100)
    width = int(w * region["w"] / 100)
    height = int(h * region["h"] / 100)
    return {"left": left, "top": top, "width": width, "height": height}


def capture_region(hwnd: int, region: dict) -> Image.Image:
    """抓取指定百分比区域，返回 PIL.Image。"""
    rect = get_client_rect(hwnd)
    box = region_to_pixels(rect, region)
    with mss.mss() as sct:
        shot = sct.grab(box)
    return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
