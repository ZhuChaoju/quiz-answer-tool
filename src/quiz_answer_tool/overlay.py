# -*- coding: utf-8 -*-
"""答题浮窗：可挪动的置顶小窗，红框样式显示识别结果（参考 175dt 观感）。

- 无边框置顶，标题把手区拖动挪位，位置按活动模块分别记忆；
- 「答案：XXX」红字 + 红色描边框突出正确答案；
- 可选鼠标穿透（穿透时点击落到游戏上，需回主窗口关闭穿透后才能再拖动）。
工具只做展示，绝不向游戏窗口发送任何输入。
"""

from __future__ import annotations

import tkinter as tk

ANSWER_FG = "#ff3c3c"
QUESTION_FG = "#e8e8e8"
NOTE_FG = "#9a9a9a"
DRAG_BG = "#101418"


class AnswerOverlay:
    """答案浮窗；由主窗口创建/销毁，recognize 结果通过 update() 推送。"""

    def __init__(self, app: tk.Tk, on_close):
        self._app = app
        self._on_close = on_close
        self._drag = None
        self.win = tk.Toplevel(app)
        self.win.title("答题浮窗")
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg=DRAG_BG)
        self.win.protocol("WM_DELETE_WINDOW", self.close)

        pad = tk.Frame(self.win, bg="#3a76d0", height=6)
        pad.pack(fill="x")
        for seq, handler in (
            ("<ButtonPress-1>", self._on_press),
            ("<B1-Motion>", self._on_drag),
            ("<ButtonRelease-1>", self._on_release),
        ):
            pad.bind(seq, handler)

        self._q = tk.Label(
            self.win, text="（等待识别）", fg=QUESTION_FG, bg=DRAG_BG,
            font=("Microsoft YaHei", 10), wraplength=340, justify="left",
        )
        self._q.pack(anchor="w", padx=10, pady=(6, 0))
        self._a = tk.Label(
            self.win, text="答案：-", fg=ANSWER_FG, bg=DRAG_BG,
            font=("Microsoft YaHei", 17, "bold"),
        )
        self._a.pack(anchor="w", padx=10, pady=(2, 2))
        # 红色描边框：贴着答案文本的装饰框（175dt 红框样式）
        self._a.configure(highlightbackground=ANSWER_FG, highlightcolor=ANSWER_FG, highlightthickness=2)
        self._note = tk.Label(self.win, text="", fg=NOTE_FG, bg=DRAG_BG, font=("Microsoft YaHei", 8))
        self._note.pack(anchor="w", padx=10, pady=(0, 6))

    # ---- 展示 ----
    def update(self, question: str, answer: str, note: str = "") -> None:
        self._q.configure(text=question or "（等待识别）")
        self._a.configure(text=f"答案：{answer}" if answer else "答案：未命中")
        self._note.configure(text=note)

    def move_to(self, x: int, y: int) -> None:
        self.win.geometry(f"+{x}+{y}")

    # ---- 穿透 ----
    def set_clickthrough(self, enabled: bool) -> None:
        import ctypes

        hwnd = ctypes.windll.user32.GetParent(self.win.winfo_id())
        GWL_EXSTYLE = -20
        WS_EX_LAYERED, WS_EX_TRANSPARENT = 0x80000, 0x20
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if enabled:
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT)
            self.win.attributes("-alpha", 0.82)
        else:
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style & ~WS_EX_TRANSPARENT)
            self.win.attributes("-alpha", 1.0)

    # ---- 拖动 ----
    def _on_press(self, event) -> None:
        self._drag = (event.x, event.y)

    def _on_drag(self, event) -> None:
        if self._drag is None:
            return
        x = self.win.winfo_x() + event.x - self._drag[0]
        y = self.win.winfo_y() + event.y - self._drag[1]
        self.win.geometry(f"+{x}+{y}")
        if self._on_close:
            self._on_close(x, y)  # 实时回传位置，主窗口随关闭时保存

    def _on_release(self, _event) -> None:
        self._drag = None

    def close(self) -> None:
        try:
            self.win.destroy()
        except tk.TclError:
            pass
