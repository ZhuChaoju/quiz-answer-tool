"""模拟点击：相对百分比坐标 → 客户区像素 → 屏幕绝对坐标。"""

from __future__ import annotations

import pyautogui

from .window import client_to_screen, get_client_rect


def click_relative(hwnd: int, x_pct: float, y_pct: float, dry_run: bool = False) -> None:
    """按窗口客户区百分比坐标点击。dry_run 时不真正点击。"""
    rect = get_client_rect(hwnd)
    w = rect.right - rect.left
    h = rect.bottom - rect.top
    client_x = int(w * x_pct / 100)
    client_y = int(h * y_pct / 100)
    screen_x, screen_y = client_to_screen(hwnd, client_x, client_y)
    if dry_run:
        return
    pyautogui.click(screen_x, screen_y)
