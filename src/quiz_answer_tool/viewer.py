# -*- coding: utf-8 -*-
"""主窗口：预览 + 识别区域(ROI) + 答案红框 + 答题浮窗 + 答案录入。

活动=模块化（banks/ 目录装配：科举乡试/会试、教师节看图说话、元宵节……），
每个模块绑定各自题库/素材库与识别区域预设。识别区域可锁定防误触，
可只显示识别区域内容；识别结果同时画到预览红框并推送到可挪动的答题浮窗。
工具只做屏幕识别与展示，不向游戏窗口发送任何输入。
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from . import ocr, screen
from .activities import BaseModule, ModuleResult, load_modules
from .overlay import AnswerOverlay

PREVIEW_FPS = 30
ANSWER_COLOR = "#ff4040"
ROI_COLORS = {"question": "#00ff00", "option": "#00aaff", "icon": "#ff9900", "search": "#bbbb00"}
DRAGGABLE_ROIS = ("question", "option", "icon")  # search 仅展示
OPTION_PAD = 0.02  # 选项区裁剪外扩（与模块识别一致），红框换算用


def _dhash(img: Image.Image) -> int:
    """8x8 感知哈希：识别区域画面是否变化的快速判据（毫秒级）。"""
    g = img.convert("L").resize((9, 8), Image.BILINEAR)
    px = list(g.getdata())
    bits = 0
    for y in range(8):
        row = y * 9
        for x in range(8):
            bits = (bits << 1) | int(px[row + x] < px[row + x + 1])
    return bits


class Viewer(tk.Tk):
    def __init__(self, cfg: dict, modules: list[BaseModule], config_path: str = "config.json"):
        super().__init__()
        self.title("答题识别工具（仅展示，不操作游戏）")
        self.cfg = cfg
        self.config_path = config_path
        self.modules = modules
        ui = cfg.get("ui", {})
        self._lock_by_mod: dict[str, bool] = {}
        self._locked = tk.BooleanVar(value=False)
        self._roi_only = tk.BooleanVar(value=bool(ui.get("roi_only", False)))
        self._overlay_on = tk.BooleanVar(value=bool(ui.get("overlay", True)))
        self._clickthrough = tk.BooleanVar(value=False)

        self._result_queue: queue.Queue = queue.Queue()
        self._preview_queue: queue.Queue = queue.Queue(maxsize=1)
        self._running = False
        self._generation = 0
        self._overlay: AnswerOverlay | None = None
        self._drag = None
        self._result: ModuleResult | None = None
        self._sources: list = []
        self._target_size = (900, 720)  # 预览线程出图尺寸（渲染时按画布更新）
        self._roi_only_flag = bool(ui.get("roi_only", False))  # 线程读的平铺副本（Tk 变量只在线程外读写）
        self._auto_start_done = False

        self._source = tk.StringVar()
        self._img: Image.Image | None = None  # 当前显示图（全画面或 ROI 并集裁剪）
        self._img_rect: tuple[float, float, float, float] | None = None  # 显示图对应全画面像素矩形
        self._full_size: tuple[int, int] | None = None
        self._items: dict[str, object] = {}
        self._scale = 1.0
        self._offset = (0.0, 0.0)
        self._drag = None
        self._result: ModuleResult | None = None

        if not modules:
            raise RuntimeError("banks/ 目录下没有可用活动模块")
        self._module = modules[0]
        sel = ui.get("module")
        for m in modules:
            if m.id == sel:
                self._module = m
        self._locked.set(self._module_lock_default())

        self._build_ui()
        self.geometry("1400x950")
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{max(sw - self.winfo_width() - 20, 0)}+{max((sh - self.winfo_height()) // 2, 0)}")
        self.after(16, self._poll_queues)
        # 自动开始：启动即自动选源并进入识别循环（可被 ui.autostart=false 关闭）
        if ui.get("autostart", True):
            self.after(1200, self._auto_start)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _auto_start(self) -> None:
        """启动即自动开始：选好来源后直接进入识别循环，无需点按钮。"""
        if self._running or self._auto_start_done:
            return
        self._reload_sources()
        if self._current_source() is None:
            self.after(2000, self._auto_start)  # 还没有可用来源（如游戏未启动），稍后重试
            return
        self._auto_start_done = True
        self._toggle()

    # ---------- UI ----------
    def _build_ui(self) -> None:
        top = ttk.Frame(self, padding=6)
        top.pack(fill="x")
        ttk.Label(top, text="活动:").pack(side="left")
        self._mod_box = ttk.Combobox(
            top, state="readonly", width=16, values=[m.name for m in self.modules]
        )
        self._mod_box.current([m.id for m in self.modules].index(self._module.id))
        self._mod_box.pack(side="left", padx=(6, 14))
        self._mod_box.bind("<<ComboboxSelected>>", self._on_module_changed)
        ttk.Label(top, text="画面来源:").pack(side="left")
        self._source_box = ttk.Combobox(top, state="readonly", width=40, textvariable=self._source)
        self._source_box.pack(side="left", padx=6)
        ttk.Button(top, text="刷新来源", command=self._reload_sources).pack(side="left")
        self._start_btn = ttk.Button(top, text="开始", command=self._toggle)
        self._start_btn.pack(side="right")
        self._lock_btn = ttk.Checkbutton(
            top, text="锁定识别区域", variable=self._locked, command=self._update_roi_label
        )
        self._lock_btn.pack(side="right", padx=8)
        ttk.Button(top, text="保存为预设", command=self._save_preset).pack(side="right", padx=6)

        second = ttk.Frame(self, padding=(6, 0))
        second.pack(fill="x")
        self._roi_only.trace_add("write", self._on_roi_only_changed)
        ttk.Checkbutton(
            second, text="只显示识别区域", variable=self._roi_only, command=self._clear_display
        ).pack(side="left")
        ttk.Checkbutton(second, text="答题浮窗", variable=self._overlay_on, command=self._sync_overlay).pack(
            side="left", padx=(14, 0)
        )
        ttk.Checkbutton(second, text="浮窗鼠标穿透", variable=self._clickthrough, command=self._sync_overlay).pack(
            side="left", padx=(14, 0)
        )
        ttk.Label(second, text="（锁定后拖动预览中的框不会影响识别；解锁拖完可「保存为预设」）", foreground="#777").pack(
            side="left", padx=14
        )

        self._canvas = tk.Canvas(self, bg="#222", highlightthickness=0)
        self._canvas.pack(fill="both", expand=True, padx=6, pady=4)
        self._canvas.bind("<ButtonPress-1>", self._on_press)
        self._canvas.bind("<B1-Motion>", self._on_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_release)

        panel = ttk.Frame(self, padding=6)
        panel.pack(fill="x")
        self._q_text = self._readonly_text(panel, height=2)
        self._a_text = self._readonly_text(panel, height=1, fg="#c00", bold=True, font_size=16)
        self._raw_text = self._readonly_text(panel, height=3, fg="#666")
        self._set_text(self._q_text, "题目: -")
        self._set_text(self._a_text, "答案: -")
        self._set_text(self._raw_text, "识别文本: -")

        row = ttk.Frame(panel)
        row.pack(fill="x", pady=(4, 0))
        self._entry_var = tk.StringVar()
        ttk.Label(row, text="录入答案:").pack(side="left")
        entry = ttk.Entry(row, textvariable=self._entry_var, width=36)
        entry.pack(side="left", padx=6)
        entry.bind("<Return>", lambda _e: self._add_answer())
        ttk.Button(row, text="收录", command=self._add_answer).pack(side="left")
        self._roi_var = tk.StringVar()
        ttk.Label(row, textvariable=self._roi_var, foreground="#666").pack(side="right")
        self._update_roi_label()
        self._reload_sources()
        self._sync_overlay(initial=True)

    def _readonly_text(
        self, master, height: int, fg: str = "#000", bold: bool = False, font_size: int = 10
    ) -> tk.Text:
        font = ("TkDefaultFont", font_size, "bold" if bold else "normal")
        text = tk.Text(
            master, height=height, wrap="word", relief="flat", highlightthickness=0,
            padx=2, pady=1, font=font, fg=fg, bg="#f8f8f8", cursor="arrow",
        )
        text.bind("<Key>", self._block_edit)
        text.pack(fill="x")
        return text

    @staticmethod
    def _block_edit(event) -> str | None:
        if event.state & 0x4:
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

    # ---------- 模块切换 / 配置 ----------
    def _module_lock_default(self) -> bool:
        per = self.cfg.get("ui", {}).get("locked", {})
        if isinstance(per, dict) and self._module.id in per:
            return bool(per[self._module.id])
        return bool(getattr(self._module, "locked_default", False))

    def _on_module_changed(self, _event=None) -> None:
        self._module = self.modules[self._mod_box.current()]
        self._locked.set(self._module_lock_default())
        self._result = None
        self._clear_display()
        self._sync_overlay()
        if self._overlay and self._overlay.win.winfo_exists():
            pos = self.cfg.get("ui", {}).get("overlay_pos", {}).get(self._module.id)
            if pos:
                self._overlay.move_to(int(pos[0]), int(pos[1]))
        self._update_roi_label()

    def _on_roi_only_changed(self, *_args) -> None:
        """主线程同步平铺标志，预览线程只读平铺值（Tk 变量本身不跨线程）。"""
        self._roi_only_flag = bool(self._roi_only.get())

    def _clear_display(self) -> None:
        self._img = None
        self._canvas.delete("all")
        self._items = {}

    def _save_preset(self) -> None:
        path = self._module.save_rois({"locked": bool(self._locked.get())})
        self._set_text(self._a_text, f"已保存识别区域预设: {path}" if path else "该模块没有可写的配置文件")

    def _save_config(self) -> None:
        """把浮窗位置/界面状态写回 config.json（按活动分别记忆）。"""
        data = dict(self.cfg)
        ui = dict(data.get("ui", {}))
        ui["module"] = self._module.id
        ui["roi_only"] = bool(self._roi_only.get())
        ui["overlay"] = bool(self._overlay_on.get())
        ui["locked"] = {**ui.get("locked", {}), self._module.id: bool(self._locked.get())}
        overlay_pos = dict(ui.get("overlay_pos", {}))
        for mid, pos in getattr(self, "_overlay_pos_by_mod", {}).items():
            overlay_pos[mid] = list(pos)
        if self._overlay and self._overlay.win.winfo_exists():
            overlay_pos[self._module.id] = [self._overlay.win.winfo_x(), self._overlay.win.winfo_y()]
        ui["overlay_pos"] = overlay_pos
        data["ui"] = ui
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    # ---------- 浮窗 ----------
    def _sync_overlay(self, initial: bool = False) -> None:
        if self._overlay_on.get():
            if self._overlay is None or not self._overlay.win.winfo_exists():
                self._overlay = AnswerOverlay(self, on_close=self._remember_overlay_pos)
                pos = self.cfg.get("ui", {}).get("overlay_pos", {}).get(self._module.id)
                if pos:
                    self._overlay.move_to(int(pos[0]), int(pos[1]))
                else:  # 默认放屏幕右上角
                    self._overlay.move_to(max(self.winfo_screenwidth() - 400, 0), 80)
            self._overlay.set_clickthrough(bool(self._clickthrough.get()))
        elif self._overlay and self._overlay.win.winfo_exists():
            self._overlay.close()
            self._overlay = None

    def _remember_overlay_pos(self, x: int, y: int) -> None:
        """浮窗拖动时实时回传位置，随主窗口关闭写回 config（按模块记忆）。"""
        if not hasattr(self, "_overlay_pos_by_mod"):
            self._overlay_pos_by_mod = {}
        self._overlay_pos_by_mod[self._module.id] = (x, y)

    # ---------- 来源 ----------
    def _reload_sources(self) -> None:
        self._sources = screen.list_sources()
        names = [s.name for s in self._sources]
        self._source_box["values"] = names
        if not names:
            return
        # 窗口优先级：含关键词且含 ONLINE 的游戏主窗口 > 含关键词 > 第一个窗口
        # （游戏有个独立悬浮窗"梦幻西游 聊天窗口"也会命中关键词，必须排后面）
        keyword = self.cfg.get("window_keyword", "")

        def rank(s) -> int:
            if s.kind == "window" and keyword and keyword in s.name:
                return 0 if "ONLINE" in s.name.upper() else 1
            return 2

        windows = [(rank(s), i) for i, s in enumerate(self._sources)]
        windows.sort()
        self._source_box.current(windows[0][1])

    def _current_source(self):
        idx = self._source_box.current()
        if 0 <= idx < len(self._sources):
            return self._sources[idx]
        return None

    # ---------- 渲染 ----------
    def _union_rect(self) -> tuple[float, float, float, float] | None:
        """模块识别区域的并集像素矩形（仅识别区域显示模式用）。"""
        if self._full_size is None:
            return None
        rects = [
            self._module.rois[k].rect_px(self._full_size)
            for k in self._module.ROI_KEYS
            if k != "search"
        ]
        if not rects:
            return None
        l = min(r[0] for r in rects)
        t = min(r[1] for r in rects)
        r = max(r[2] for r in rects)
        b = max(r[3] for r in rects)
        return max(l, 0), max(t, 0), min(r, self._full_size[0]), min(b, self._full_size[1])

    def _render(self, img: Image.Image, img_rect: tuple[float, float, float, float], full_size) -> None:
        self._img = img
        self._img_rect = img_rect
        self._full_size = full_size
        cw = max(self._canvas.winfo_width(), 200)
        ch = max(self._canvas.winfo_height(), 150)
        rw = max(img_rect[2] - img_rect[0], 1.0)
        rh = max(img_rect[3] - img_rect[1], 1.0)
        # scale = 画布像素 / 整帧像素；图片必须真正缩放到 disp 尺寸再显示，
        # 否则框（按 scale 画）和图片（按原生尺寸显示）比例不一致会错位。
        # 4K 屏上限 1920 宽：足够清晰且控制 30fps 缩放开销
        self._scale = min(cw / rw, ch / rh, 1920.0 / rw)
        disp_w, disp_h = max(1, int(rw * self._scale)), max(1, int(rh * self._scale))
        self._target_size = (disp_w, disp_h)  # 预览线程按此尺寸出图
        if img.size != (disp_w, disp_h):
            img = img.resize((disp_w, disp_h), Image.BILINEAR)
        ox, oy = cw // 2 - disp_w // 2, ch // 2 - disp_h // 2
        self._offset = (ox, oy)
        photo = ImageTk.PhotoImage(img)
        self._photo = photo
        cx, cy = ox + disp_w // 2, oy + disp_h // 2
        if self._items.get("img") is None:
            self._items["img"] = self._canvas.create_image(cx, cy, image=photo, anchor="center")
        else:
            self._canvas.itemconfigure(self._items["img"], image=photo)
            self._canvas.coords(self._items["img"], cx, cy)
        self._draw_rois()
        self._draw_answer_box()

    def _to_display(self, fx: float, fy: float) -> tuple[float, float]:
        """整帧像素坐标 → 画布坐标（考虑仅识别区域模式的裁剪偏移）。"""
        ox, oy = self._offset
        if self._img_rect is not None:
            l, t, _, _ = self._img_rect
            return ox + (fx - l) * self._scale, oy + (fy - t) * self._scale
        return ox + fx * self._scale, oy + fy * self._scale

    def _to_img_coord(self, cx: float, cy: float) -> tuple[float, float]:
        ox, oy = self._offset
        if self._img_rect is not None:
            l, t, _, _ = self._img_rect
            return l + (cx - ox) / self._scale, t + (cy - oy) / self._scale
        return (cx - ox) / self._scale, (cy - oy) / self._scale

    def _draw_rois(self) -> None:
        if self._img is None or self._full_size is None:
            return
        # 图标模块选项区跟随定位：有动态矩形时蓝框画实际识别区域
        dyn = self._result.option_rect if (self._result and self._result.option_rect) else None
        for key in self._module.ROI_KEYS:
            if key == "option" and dyn is not None:
                l, t, r, b = map(float, dyn)
            else:
                l, t, r, b = self._module.rois[key].rect_px(self._full_size)
            x1, y1 = self._to_display(l, t)
            x2, y2 = self._to_display(r, b)
            color = ROI_COLORS.get(key, "#ffffff")
            item = self._items.get(key)
            width = 1 if key == "search" else 2
            if item is None:
                self._items[key] = self._canvas.create_rectangle(
                    x1, y1, x2, y2, outline=color, width=width,
                    dash=(4, 2) if key == "search" else None,
                )
            else:
                self._canvas.coords(item, x1, y1, x2, y2)

    def _draw_answer_box(self) -> None:
        """把答案定位框画到预览上（175dt 红框样式）。答案段为选项裁剪图内绝对像素。"""
        item = self._items.get("ans")
        if self._img is None or self._result is None or self._result.answer_line is None:
            if item is not None:
                self._canvas.itemconfigure(item, state="hidden")
            return
        line, sx1, sx2 = self._result.answer_line
        if self._result.option_rect is not None:
            rl, rt = float(self._result.option_rect[0]), float(self._result.option_rect[1])
        else:
            rl, rt, _, _ = self._module.rois["option"].rect_px(self._full_size, OPTION_PAD)
        pad = 4.0  # 视觉上略宽于文字，接近 175dt 的按钮框观感
        x1, y1 = self._to_display(rl + sx1 - pad, rt + line.center_y - line.height / 2 - 2)
        x2, y2 = self._to_display(rl + sx2 + pad, rt + line.center_y + line.height / 2 + 2)
        if item is None:
            self._items["ans"] = self._canvas.create_rectangle(
                x1, y1, x2, y2, outline=ANSWER_COLOR, width=3
            )
        else:
            self._canvas.coords(self._items["ans"], x1, y1, x2, y2)
            self._canvas.itemconfigure(self._items["ans"], state="normal")

    def _update_roi_label(self) -> None:
        parts = [
            f"{k}: x={r.x:.1f} y={r.y:.1f} w={r.w:.1f} h={r.h:.1f}"
            for k, r in self._module.rois.items()
            if k != "search"
        ]
        self._roi_var.set(("已锁定 " if self._locked.get() else "") + "  ".join(parts))

    # ---------- ROI 拖拽（锁定时不改识别区域） ----------
    def _on_press(self, event) -> None:
        if self._img is None or self._full_size is None:
            return
        if self._locked.get():
            self._drag = None
            return
        ix, iy = self._to_img_coord(event.x, event.y)
        for target in DRAGGABLE_ROIS:
            if target not in self._module.rois:
                continue
            roi = self._module.rois[target]
            l, t, r, b = roi.rect_px(self._full_size)
            if l <= ix <= r and t <= iy <= b:
                self._drag = {
                    "start": (ix, iy),
                    "orig": (l, t, r - l, b - t),
                    "target": target,
                    "mode": "resize" if ix > r - 14 and iy > b - 14 else "move",
                }
                return
        self._drag = None  # 不允许随手拖出新框，防止误改识别区域

    def _on_drag(self, event) -> None:
        if self._drag is None or self._img is None or self._full_size is None:
            return
        ix, iy = self._to_img_coord(event.x, event.y)
        ox, oy, ow, oh = self._drag["orig"]
        sx, sy = self._drag["start"]
        if self._drag["mode"] == "move":
            nx, ny, nw, nh = ox + (ix - sx), oy + (iy - sy), ow, oh
        else:
            nx, ny, nw, nh = ox, oy, ix - ox, iy - oy
        w, h = self._full_size
        nx, ny = max(0, min(nx, w - 1)), max(0, min(ny, h - 1))
        nw, nh = max(5, min(nw, w - nx)), max(5, min(nh, h - ny))
        self._module.rois[self._drag["target"]] = type(self._module.rois["option"])(
            x=nx / w * 100, y=ny / h * 100, w=nw / w * 100, h=nh / h * 100
        )
        self._draw_rois()
        self._draw_answer_box()
        self._update_roi_label()

    def _on_release(self, _event) -> None:
        self._drag = None

    # ---------- 运行控制 ----------
    def _toggle(self) -> None:
        if self._running:
            self._running = False
            self._generation += 1
            self._start_btn.config(text="开始")
            return
        source = self._current_source()
        if source is None:
            return
        self._running = True
        self._start_btn.config(text="停止")
        self._start_threads(source)

    def _start_threads(self, source) -> None:
        generation = self._generation

        def alive() -> bool:
            return self._running and generation == self._generation

        def preview_loop() -> None:
            period = 1.0 / PREVIEW_FPS
            while alive():
                t0 = time.perf_counter()
                try:
                    frame, _ = screen.capture(source)
                    full_size = frame.size
                    rect = (0.0, 0.0, float(full_size[0]), float(full_size[1]))
                    if self._roi_only_flag:
                        union = self._union_rect()
                        if union:
                            l, t, r, b = union
                            rect = (l, t, r, b)
                            frame = frame.crop((int(l), int(t), int(r), int(b)))
                    # 出图即缩放到渲染目标尺寸（主线程渲染时更新），框与图共用同一比例
                    target = self._target_size
                    if frame.size != target:
                        frame = frame.resize(target, Image.BILINEAR)
                    try:
                        self._preview_queue.put_nowait((frame, rect, full_size))
                    except queue.Full:
                        pass
                except Exception as exc:
                    self._result_queue.put(("error", f"截图失败: {exc}"))
                    break
                elapsed = time.perf_counter() - t0
                if elapsed < period:
                    time.sleep(period - elapsed)

        def ocr_loop() -> None:
            ocr_cfg = dict(self.cfg.get("ocr", {}))
            # 默认 0.05s：有感知哈希闸门兜底，画面静止时空转开销极低，还能更快发现新题
            interval = float(self.cfg.get("interval_sec", 0.05))
            dml = bool(ocr_cfg.get("use_dml", False))
            # 引擎预热：模型加载与首次推理秒级，点「开始」先跑空图完成（引擎参数须与正式识别一致）
            try:
                blank = Image.new("RGB", (64, 16), "white")
                ocr.recognize(blank, ocr_cfg.get("lang", "ch"), 0.6, ocr_cfg.get("model_type", "tiny"), False, dml)
                ocr.recognize(blank, ocr_cfg.get("lang", "ch"), 0.6, ocr_cfg.get("model_type", "tiny"), True, dml)
            except Exception:
                pass
            last_hash: int | None = None
            last_mod_id: str | None = None
            while alive():
                time.sleep(interval)
                mod = self._module  # 运行中切活动，下一轮立即生效
                gate_key = "question" if "question" in mod.rois else "icon"
                if mod.id != last_mod_id:
                    last_mod_id = mod.id
                    last_hash = None
                try:
                    frame, _ = screen.capture(source)
                    gate_crop = mod.rois[gate_key].crop(frame, pad=0.02)
                except Exception as exc:
                    self._result_queue.put(("error", f"截图失败: {exc}"))
                    continue
                cur = _dhash(gate_crop)
                if cur == last_hash:
                    continue
                last_hash = cur
                # 画面已变化：立即清掉上一题的红框/动态选项框，避免新题出来时残留
                self._result_queue.put(("clear",))
                try:
                    result = mod.recognize(frame, ocr_cfg)
                except Exception as exc:
                    self._result_queue.put(("error", f"识别失败: {exc}"))
                    continue
                self._result_queue.put(("result", result))

        for fn in (preview_loop, ocr_loop):
            t = threading.Thread(target=fn, daemon=True)
            t.start()

    # ---------- 答案录入 ----------
    def _add_answer(self) -> None:
        text = self._entry_var.get().strip()
        if not text:
            return
        mod = self._module
        if mod.type == "icon":
            if mod.last_hash is None:
                self._set_text(self._a_text, "没有可收录的图标（先识别一次）")
                return
            mod.bank.add(mod.last_hash, text)
            if mod.config_path():
                try:
                    mod.bank.save(os.path.join(mod.bank_dir, "icons.json"))
                except OSError as exc:
                    self._set_text(self._a_text, f"写入图标库失败: {exc}")
                    return
            self._set_text(self._a_text, f"已收录图标: {text}（共 {len(mod.bank)} 个）")
        else:
            q = getattr(mod, "last_question", "")
            if not q:
                self._set_text(self._a_text, "没有可收录的题目（先识别一次未命中题目）")
                return
            mod.bank.add(q, text)
            bank_path = os.path.join(mod.bank_dir, "questions.json")
            try:
                with open(bank_path, encoding="utf-8-sig") as f:
                    data = json.load(f)
                hit = next((it for it in data if it.get("question") == q), None)
                if hit is None:
                    data.append({"id": len(data) + 1, "question": q, "options": [], "answer": text})
                else:
                    hit["answer"] = text
                with open(bank_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=1)
            except OSError as exc:
                self._set_text(self._a_text, f"写入题库失败: {exc}")
                return
            self._set_text(self._a_text, f"已收录: {q} → {text}")
        self._entry_var.set("")

    # ---------- 队列轮询 ----------
    def _poll_queues(self) -> None:
        try:
            while True:
                img, rect, full_size = self._preview_queue.get_nowait()
                self._render(img, rect, full_size)
        except queue.Empty:
            pass
        try:
            while True:
                kind, *payload = self._result_queue.get_nowait()
                if kind == "clear":
                    # 画面变化、新题识别中：立即清掉上一题的红框与动态选项框
                    self._result = None
                    self._draw_answer_box()
                    self._draw_rois()
                elif kind == "result":
                    result: ModuleResult = payload[0]
                    self._result = result
                    self._set_text(self._q_text, f"题目: {result.question or '-'}")
                    self._set_text(self._a_text, f"答案: {result.answer}" if result.answer else "未命中")
                    raw = "\n".join(ln.text for ln in result.lines)
                    self._set_text(self._raw_text, f"识别文本: {raw}" if raw else "识别文本: -")
                    if self._overlay and self._overlay.win.winfo_exists():
                        self._overlay.update(result.question, result.answer, result.note)
                    self._draw_answer_box()
                elif kind == "error":
                    self._set_text(self._a_text, payload[0])
        except queue.Empty:
            pass
        self.after(16, self._poll_queues)

    def _on_close(self) -> None:
        self._running = False
        self._save_config()
        time.sleep(0.3)
        if self._overlay and self._overlay.win.winfo_exists():
            self._overlay.close()
        self.destroy()
