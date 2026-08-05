"""实时预览窗口：显示所选屏幕画面、可拖拽 ROI 框、答案红框高亮、答案录入。"""

from __future__ import annotations

import json
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from . import matcher, ocr, screen

PREVIEW_WIDTH = 900  # 预览显示宽度（像素），后台缩放降低主线程负载
PREVIEW_FPS = 60
OCR_ANSWER_COLOR = "#ff4040"


def _dhash(img: Image.Image) -> int:
    """8x8 感知哈希：ROI 画面是否变化的快速判据（毫秒级）。"""
    g = img.convert("L").resize((9, 8), Image.BILINEAR)
    px = list(g.getdata())
    bits = 0
    for y in range(8):
        row = y * 9
        for x in range(8):
            bits = (bits << 1) | int(px[row + x] < px[row + x + 1])
    return bits


class Viewer(tk.Tk):
    """窗口 2：预览 + ROI + 答案红框 + 录入。"""

    def __init__(self, cfg: dict, bank: matcher.QuestionBank | None, bank_path: str = "questions.json"):
        super().__init__()
        self.title("答题识别窗口")
        self.cfg = cfg
        self.bank = bank
        self.bank_path = bank_path
        self._result_queue: queue.Queue = queue.Queue()
        self._preview_queue: queue.Queue = queue.Queue(maxsize=2)
        self._running = False
        self._threads: list[threading.Thread] = []

        self._source = tk.StringVar()
        self._roi = dict(cfg.get("roi", {"x": 10, "y": 10, "w": 80, "h": 30}))
        self._img: Image.Image | None = None
        self._scale = 1.0
        self._offset = (0.0, 0.0)
        self._drag = None
        self._answer_line: ocr.Line | None = None
        self._last_question = ""

        self._build_ui()
        self.after(16, self._poll_queues)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        top = ttk.Frame(self, padding=6)
        top.pack(fill="x")
        ttk.Label(top, text="画面来源:").pack(side="left")
        self._source_box = ttk.Combobox(top, state="readonly", width=42, textvariable=self._source)
        self._source_box.pack(side="left", padx=6)
        ttk.Button(top, text="刷新来源", command=self._reload_sources).pack(side="left")
        self._start_btn = ttk.Button(top, text="开始", command=self._toggle)
        self._start_btn.pack(side="right")
        ttk.Button(top, text="重置框", command=self._reset_roi).pack(side="right", padx=6)

        self._canvas = tk.Canvas(self, bg="#222", highlightthickness=0)
        self._canvas.pack(fill="both", expand=True, padx=6)
        self._canvas.bind("<ButtonPress-1>", self._on_press)
        self._canvas.bind("<B1-Motion>", self._on_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_release)

        panel = ttk.Frame(self, padding=6)
        panel.pack(fill="x")
        self._q_var = tk.StringVar(value="题目: -")
        self._a_var = tk.StringVar(value="答案: -")
        self._raw_var = tk.StringVar(value="识别文本: -")
        ttk.Label(panel, textvariable=self._q_var, wraplength=760).pack(anchor="w")
        ttk.Label(panel, textvariable=self._a_var, font=("TkDefaultFont", 14, "bold"), foreground="#0a0").pack(anchor="w")
        ttk.Label(panel, textvariable=self._raw_var, wraplength=760, foreground="#666").pack(anchor="w")

        row = ttk.Frame(panel)
        row.pack(fill="x", pady=(4, 0))
        self._entry_var = tk.StringVar()
        ttk.Label(row, text="录入答案:").pack(side="left")
        entry = ttk.Entry(row, textvariable=self._entry_var, width=40)
        entry.pack(side="left", padx=6)
        entry.bind("<Return>", lambda _e: self._add_answer())
        ttk.Button(row, text="收录到题库", command=self._add_answer).pack(side="left")
        self._roi_var = tk.StringVar()
        ttk.Label(row, textvariable=self._roi_var, foreground="#666").pack(side="right")
        self._update_roi_label()

        self._reload_sources()

    # ---- 来源管理 ----
    def _reload_sources(self) -> None:
        self._sources = screen.list_sources()
        names = [s.name for s in self._sources]
        self._source_box["values"] = names
        if names:
            self._source_box.current(0)

    def _current_source(self) -> screen.Source | None:
        idx = self._source_box.current()
        if 0 <= idx < len(self._sources):
            return self._sources[idx]
        return None

    # ---- 预览渲染 ----
    def _render(self, img: Image.Image) -> None:
        self._img = img
        cw = max(self._canvas.winfo_width(), 200)
        ch = max(self._canvas.winfo_height(), 150)
        self._scale = min(cw / img.width, ch / img.height)
        disp_w, disp_h = int(img.width * self._scale), int(img.height * self._scale)
        ox = cw // 2 - disp_w // 2
        oy = ch // 2 - disp_h // 2
        self._offset = (ox, oy)
        self._canvas.delete("all")
        photo = ImageTk.PhotoImage(img)
        self._photo = photo
        self._canvas.create_image(ox + disp_w // 2, oy + disp_h // 2, image=photo, anchor="center")
        self._draw_roi()
        self._draw_answer_box()

    def _img_to_canvas(self, x: float, y: float) -> tuple[float, float]:
        ox, oy = self._offset
        return ox + x * self._scale, oy + y * self._scale

    def _draw_roi(self) -> None:
        if self._img is None:
            return
        w, h = self._img.size
        rx, ry = self._roi["x"] / 100 * w, self._roi["y"] / 100 * h
        rw, rh = self._roi["w"] / 100 * w, self._roi["h"] / 100 * h
        x1, y1 = self._img_to_canvas(rx, ry)
        x2, y2 = self._img_to_canvas(rx + rw, ry + rh)
        self._canvas.create_rectangle(x1, y1, x2, y2, outline="#00ff00", width=2, tags="roi")
        self._canvas.create_rectangle(x2 - 10, y2 - 10, x2, y2, fill="#00ff00", outline="", tags="roi")

    def _draw_answer_box(self) -> None:
        if self._img is None or self._answer_line is None:
            return
        w, h = self._img.size
        roi = self._roi
        ax = (roi["x"] + self._answer_line.center_x / (w * roi["w"] / 100) * roi["w"]) / 100 * w
        ay = (roi["y"] + self._answer_line.center_y / (h * roi["h"] / 100) * roi["h"]) / 100 * h
        aw = self._answer_line.width / (w * roi["w"] / 100) * roi["w"] / 100 * w
        ah = self._answer_line.height / (h * roi["h"] / 100) * roi["h"] / 100 * h
        x1, y1 = self._img_to_canvas(ax - aw / 2, ay - ah / 2)
        x2, y2 = self._img_to_canvas(ax + aw / 2, ay + ah / 2)
        self._canvas.create_rectangle(x1, y1, x2, y2, outline=OCR_ANSWER_COLOR, width=3, tags="ans")

    # ---- ROI 拖拽 ----
    def _to_img_coord(self, cx: float, cy: float) -> tuple[float, float]:
        ox, oy = self._offset
        return (cx - ox) / self._scale, (cy - oy) / self._scale

    def _on_press(self, event) -> None:
        if self._img is None:
            return
        ix, iy = self._to_img_coord(event.x, event.y)
        w, h = self._img.size
        rx = self._roi["x"] / 100 * w
        ry = self._roi["y"] / 100 * h
        rw = self._roi["w"] / 100 * w
        rh = self._roi["h"] / 100 * h
        inside = rx <= ix <= rx + rw and ry <= iy <= ry + rh
        on_handle = ix > rx + rw - 14 and iy > ry + rh - 14
        self._drag = {"start": (ix, iy), "orig": (rx, ry, rw, rh)}
        self._drag["mode"] = "resize" if (inside and on_handle) or not inside else "move"
        if not inside:
            self._drag["mode"] = "create"

    def _on_drag(self, event) -> None:
        if self._drag is None or self._img is None:
            return
        ix, iy = self._to_img_coord(event.x, event.y)
        ox, oy, ow, oh = self._drag["orig"]
        sx, sy = self._drag["start"]
        mode = self._drag["mode"]
        if mode == "move":
            nx, ny, nw, nh = ox + (ix - sx), oy + (iy - sy), ow, oh
        elif mode == "resize":
            nx, ny, nw, nh = ox, oy, ix - ox, iy - oy
        else:
            nx, ny = min(sx, ix), min(sy, iy)
            nw, nh = abs(ix - sx), abs(iy - sy)
        w, h = self._img.size
        nx = max(0, min(nx, w - 1))
        ny = max(0, min(ny, h - 1))
        nw = max(5, min(nw, w - nx))
        nh = max(5, min(nh, h - ny))
        self._roi = {"x": nx / w * 100, "y": ny / h * 100, "w": nw / w * 100, "h": nh / h * 100}
        self._draw_roi()
        self._draw_answer_box()
        self._update_roi_label()

    def _on_release(self, _event) -> None:
        self._drag = None

    def _reset_roi(self) -> None:
        self._roi = dict(self.cfg.get("roi", {"x": 10, "y": 10, "w": 80, "h": 30}))
        self._draw_roi()
        self._update_roi_label()

    def _update_roi_label(self) -> None:
        self._roi_var.set(
            f"ROI: x={self._roi['x']:.1f}% y={self._roi['y']:.1f}% "
            f"w={self._roi['w']:.1f}% h={self._roi['h']:.1f}%"
        )

    # ---- 运行控制 ----
    def _toggle(self) -> None:
        if self._running:
            self._running = False
            self._start_btn.config(text="开始")
            return
        source = self._current_source()
        if source is None:
            return
        self._running = True
        self._start_btn.config(text="停止")
        self._start_threads(source)

    def _start_threads(self, source: screen.Source) -> None:
        def preview_loop() -> None:
            period = 1.0 / PREVIEW_FPS
            while self._running:
                t0 = time.perf_counter()
                try:
                    img, _ = screen.capture(source)
                    ratio = PREVIEW_WIDTH / img.width
                    if ratio < 1.0:
                        img = img.resize(
                            (PREVIEW_WIDTH, max(1, int(img.height * ratio))),
                            Image.BILINEAR,
                        )
                    try:
                        self._preview_queue.put_nowait(img)
                    except queue.Full:
                        pass
                except Exception as exc:
                    self._result_queue.put(("error", f"截图失败: {exc}"))
                    break
                elapsed = time.perf_counter() - t0
                if elapsed < period:
                    time.sleep(period - elapsed)

        def ocr_loop() -> None:
            ocr_cfg = self.cfg.get("ocr", {})
            interval = self.cfg.get("interval_sec", 0.2)
            last_key: tuple | None = None
            last_hash: int | None = None
            while self._running:
                time.sleep(interval)
                try:
                    img, _ = screen.capture(source)
                    crop = screen.crop_region(img, self._roi)
                except Exception as exc:
                    self._result_queue.put(("error", f"截图失败: {exc}"))
                    continue
                cur_hash = _dhash(crop)
                if cur_hash == last_hash:
                    continue
                last_hash = cur_hash
                try:
                    lines = ocr.recognize(crop, ocr_cfg.get("lang", "ch"), ocr_cfg.get("confidence", 0.6))
                except Exception as exc:
                    self._result_queue.put(("error", f"识别失败: {exc}"))
                    continue
                if not lines:
                    continue
                key = tuple(ln.text for ln in lines[:2])
                if key == last_key:
                    continue
                last_key = key
                question = self.bank.match(lines[0].text) if self.bank else None
                answer = question.get("answer", "") if question else ""
                answer_line = self._find_answer_line(lines[1:], answer) if answer else None
                self._result_queue.put(("result", lines, question, answer, answer_line))

        for fn in (preview_loop, ocr_loop):
            t = threading.Thread(target=fn, daemon=True)
            t.start()
            self._threads.append(t)

    @staticmethod
    def _find_answer_line(lines: list[ocr.Line], answer: str) -> ocr.Line | None:
        from difflib import SequenceMatcher

        answer = answer.strip()
        if not answer:
            return None
        for ln in lines:
            text = ln.text.strip()
            if text and (text == answer or answer in text or text in answer):
                return ln
        best: ocr.Line | None = None
        best_ratio = 0.0
        for ln in lines:
            text = ln.text.strip()
            if not text:
                continue
            ratio = SequenceMatcher(None, answer, text).ratio()
            if ratio > best_ratio:
                best, best_ratio = ln, ratio
        return best if best_ratio >= 0.7 else None

    # ---- 答案录入（收录到题库） ----
    def _add_answer(self) -> None:
        text = self._entry_var.get().strip()
        if not text or not self._last_question:
            return
        if self.bank is not None:
            self.bank.add(self._last_question, text)
        try:
            with open(self.bank_path, encoding="utf-8") as f:
                data = json.load(f)
            if not any(item.get("question") == self._last_question for item in data):
                data.append({"id": len(data) + 1, "question": self._last_question, "options": [], "answer": text})
                with open(self.bank_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=1)
        except OSError as exc:
            self._a_var.set(f"写入题库失败: {exc}")
            return
        self._a_var.set(f"已收录: {self._last_question} → {text}")
        self._entry_var.set("")

    # ---- 队列轮询 ----
    def _poll_queues(self) -> None:
        try:
            while True:
                img = self._preview_queue.get_nowait()
                self._render(img)
        except queue.Empty:
            pass
        try:
            while True:
                kind, *payload = self._result_queue.get_nowait()
                if kind == "result":
                    lines, question, answer, answer_line = payload
                    self._last_question = lines[0].text
                    self._answer_line = answer_line
                    self._q_var.set(f"题目: {lines[0].text}")
                    self._a_var.set(f"答案: {answer}" if answer else "未命中")
                    raw = " | ".join(ln.text for ln in lines)
                    self._raw_var.set(f"识别文本: {raw}")
                    self._draw_answer_box()
                elif kind == "error":
                    self._a_var.set(payload[0])
        except queue.Empty:
            pass
        self.after(16, self._poll_queues)

    def _on_close(self) -> None:
        self._running = False
        time.sleep(0.3)
        self.destroy()
