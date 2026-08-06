"""实时预览窗口：显示所选屏幕画面、可拖拽 ROI 框、答案红框高亮、答案录入。"""

from __future__ import annotations

import json
import queue
import re
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
        self._full_size: tuple[int, int] | None = None  # 原始截图尺寸（OCR 坐标基准）
        self._scale = 1.0
        self._offset = (0.0, 0.0)
        self._drag = None
        self._answer_line: ocr.Line | None = None
        self._last_question = ""

        self._build_ui()
        # 默认窗口尺寸放大（预览 900px 宽 + 底部信息面板），贴屏幕右缘显示
        # （游戏窗口通常放左边，工具窗口放右边便于对照）
        self.geometry("1600x1000")
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x = max(sw - self.winfo_width() - 20, 0)
        y = max((sh - self.winfo_height()) // 2, 0)
        self.geometry(f"+{x}+{y}")
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
        # 固定行数：防止文字换行改变底部面板高度，导致预览画布被挤动、画面跳动；
        # 用只读 Text 代替 Label，便于鼠标选中复制识别文本
        self._q_text = self._readonly_text(panel, height=3)
        self._a_text = self._readonly_text(panel, height=2, fg="#0a0", bold=True, font_size=16)
        self._raw_text = self._readonly_text(panel, height=4, fg="#666")
        self._set_text(self._q_text, "题目: -")
        self._set_text(self._a_text, "答案: -")
        self._set_text(self._raw_text, "识别文本: -")

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

    # ---- 底部只读文本（可选中复制） ----
    def _readonly_text(
        self,
        master: tk.Widget,
        height: int,
        fg: str = "#000",
        bold: bool = False,
        font_size: int = 10,
    ) -> tk.Text:
        """创建只读多行文本框：鼠标可选、Ctrl+C 可复制，但不能编辑。"""
        font = ("TkDefaultFont", font_size, "bold" if bold else "normal")
        text = tk.Text(
            master,
            height=height,
            wrap="word",
            relief="flat",
            highlightthickness=0,
            padx=2,
            pady=1,
            font=font,
            fg=fg,
            bg="#f8f8f8",
            cursor="arrow",
        )
        text.bind("<Key>", self._block_edit)
        text.pack(fill="x")
        return text

    @staticmethod
    def _block_edit(event: tk.Event) -> str | None:
        """只读：放行复制/全选等 Ctrl 组合键，拦截普通输入与删除键。"""
        if event.state & 0x4:  # Ctrl 按下
            return None
        if event.keysym in ("BackSpace", "Delete", "Return", "Tab", "space"):
            return "break"
        if event.char and event.char.isprintable():
            return "break"
        return None

    @staticmethod
    def _set_text(widget: tk.Text, text: str) -> None:
        widget.delete("1.0", "end")
        widget.insert("1.0", text)

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
    def _render(self, img: Image.Image, full_size: tuple[int, int]) -> None:
        self._img = img
        self._full_size = full_size
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
        if self._img is None or self._answer_line is None or self._full_size is None:
            return
        line, left, right = self._answer_line
        # OCR 基于 ROI 裁剪图识别：先换算回原图坐标（加 ROI 偏移），再换算到显示图坐标
        fw, fh = self._full_size
        ratio_x = self._img.width / fw
        ratio_y = self._img.height / fh
        roi_x = fw * self._roi["x"] / 100
        roi_y = fh * self._roi["y"] / 100
        ax = (roi_x + line.center_x) * ratio_x
        ay = (roi_y + line.center_y) * ratio_y
        half_w = line.width / 2 * ratio_x
        x1, y1 = self._img_to_canvas(ax - half_w + line.width * left * ratio_x, ay - line.height / 2 * ratio_y)
        x2, y2 = self._img_to_canvas(ax - half_w + line.width * right * ratio_x, ay + line.height / 2 * ratio_y)
        self._canvas.create_rectangle(x1, y1, x2, y2, outline=OCR_ANSWER_COLOR, width=3, tags="ans")

    @staticmethod
    def _is_ui_noise(text: str) -> bool:
        """系统 UI 噪声行：标题、按钮、进度提示、关卡提示等，不影响识别结果。"""
        t = text.strip()
        if len(t) <= 1:  # 如 "问" 按钮
            return True
        if re.search(
            r"离开答题|当前第\s*\d|还可以答|附加考题?|附加题|第\d+题"
            r"|连对|科举大赛第?\s*\d*\s*关|这一关考的是|殿试部分",
            t,
        ):
            return True
        return False

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
                    full_size = img.size  # 记录原始尺寸，OCR 红框换算依赖它
                    ratio = PREVIEW_WIDTH / img.width
                    if ratio < 1.0:
                        img = img.resize(
                            (PREVIEW_WIDTH, max(1, int(img.height * ratio))),
                            Image.BILINEAR,
                        )
                    try:
                        self._preview_queue.put_nowait((img, full_size))
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
                    # 按 ROI 裁剪识别：绿框内包含题目与选项，框外内容不参与识别
                    lines = ocr.recognize(crop, ocr_cfg.get("lang", "ch"), ocr_cfg.get("confidence", 0.6))
                except Exception as exc:
                    self._result_queue.put(("error", f"识别失败: {exc}"))
                    continue
                if not lines:
                    continue
                # 剔除系统 UI 噪声行（标题、按钮、进度提示等），只留题目与选项，
                # 这样 ROI 框大一些也不会被其他文字干扰匹配与红框定位
                lines = [ln for ln in lines if not self._is_ui_noise(ln.text)]
                if not lines:
                    continue
                key = tuple(ln.text for ln in lines[:2])
                if key == last_key:
                    continue
                last_key = key
                # 题目匹配：优先取 ROI 内的行（用户框的题目区），用最长行匹配；
                # 未命中再用合并全文兜底
                main_line = max(lines, key=lambda ln: len(ln.text))
                full_text = "".join(ln.text for ln in lines)
                question = None
                if self.bank is not None:
                    question = self.bank.match(main_line.text)
                    if question is None:
                        question = self.bank.match(full_text)
                answer = question.get("answer", "") if question else ""
                answer_line = self._find_answer_line(lines[1:], answer) if answer else None
                self._result_queue.put(("result", lines, question, answer, answer_line))

        for fn in (preview_loop, ocr_loop):
            t = threading.Thread(target=fn, daemon=True)
            t.start()
            self._threads.append(t)

    @staticmethod
    def _find_answer_line(lines: list[ocr.Line], answer: str) -> tuple[ocr.Line, float, float] | None:
        """在识别行中定位答案所在行，返回 (行, 答案文本在行内的左右比例, 右比例)。

        选项行通常带 A、B、C、D 前缀且一行含多个选项，用比例把红框精确到
        单个选项，而不是圈整行。
        """
        from difflib import SequenceMatcher
        import re

        # 剥离行首的选项前缀，如 "A、" "B." "1、" "2、" 等
        prefix_re = re.compile(r"^[A-Za-z一二三四五六七八九十百\d]+[、.．:：]\s*")

        def clean(text: str) -> str:
            return prefix_re.sub("", text.strip())

        answer = answer.strip()
        if not answer:
            return None
        # 答案可能含 "/" 分隔的多段（如 "及时好雨润新绿／送暖春风过万家"），任一命中即可
        answer_parts = [p.strip() for p in re.split(r"[/／]", answer) if p.strip()]
        for ln in lines:
            text = clean(ln.text)
            if not text:
                continue
            for part in answer_parts:
                if part == text or part in text or text in part:
                    idx = text.find(part)
                    if idx >= 0:
                        left = idx / max(len(text), 1)
                        right = (idx + len(part)) / max(len(text), 1)
                    else:
                        left, right = 0.0, 1.0
                    return ln, left, right
        best: ocr.Line | None = None
        best_ratio = 0.0
        for ln in lines:
            text = clean(ln.text)
            if not text:
                continue
            ratio = max(SequenceMatcher(None, part, text).ratio() for part in answer_parts)
            if ratio > best_ratio:
                best, best_ratio = ln, ratio
        return (best, 0.0, 1.0) if best and best_ratio >= 0.7 else None

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
            self._set_text(self._a_text, f"写入题库失败: {exc}")
            return
        self._set_text(self._a_text, f"已收录: {self._last_question} → {text}")
        self._entry_var.set("")

    # ---- 队列轮询 ----
    def _poll_queues(self) -> None:
        try:
            while True:
                img, full_size = self._preview_queue.get_nowait()
                self._render(img, full_size)
        except queue.Empty:
            pass
        try:
            while True:
                kind, *payload = self._result_queue.get_nowait()
                if kind == "result":
                    lines, question, answer, answer_line = payload
                    # 题目栏显示题库命中的原文（干净无"御前科举大赛第X关"等前缀），
                    # 未命中则显示识别到的第一行
                    q_display = question.get("question", "") if question else lines[0].text
                    self._last_question = q_display
                    self._answer_line = answer_line
                    self._set_text(self._q_text, f"题目: {q_display}")
                    self._set_text(self._a_text, f"答案: {answer}" if answer else "未命中")
                    raw = "\n".join(ln.text for ln in lines)
                    self._set_text(self._raw_text, f"识别文本: {raw}")
                    self._draw_answer_box()
                elif kind == "error":
                    self._set_text(self._a_text, payload[0])
        except queue.Empty:
            pass
        self.after(16, self._poll_queues)

    def _on_close(self) -> None:
        self._running = False
        time.sleep(0.3)
        self.destroy()
