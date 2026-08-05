"""窗口枚举与客户区矩形获取（Windows）。"""

from __future__ import annotations

import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


def list_windows() -> list[tuple[int, str]]:
    """返回所有可见顶层窗口的 [(hwnd, title)]。"""
    result: list[tuple[int, str]] = []

    def callback(hwnd: int, _: object) -> bool:
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                result.append((hwnd, buf.value))
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(callback), 0)
    return result


def find_window(keyword: str) -> int | None:
    """按标题关键词查找窗口，返回 hwnd；未命中返回 None。"""
    if not keyword:
        return None
    for hwnd, title in list_windows():
        if keyword in title:
            return hwnd
    return None


def get_client_rect(hwnd: int) -> RECT:
    """获取窗口客户区矩形（屏幕坐标）。"""
    rect = RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    origin = wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(origin))
    return RECT(origin.x, origin.y, origin.x + rect.right, origin.y + rect.bottom)


def client_to_screen(hwnd: int, x: int, y: int) -> tuple[int, int]:
    """客户区坐标转屏幕坐标。"""
    pt = wintypes.POINT(x, y)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    return pt.x, pt.y
