"""实时预览窗口：显示所选屏幕画面、可拖拽 ROI 框、答案红框高亮、答案录入。"""

from __future__ import annotations

import concurrent.futures
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
PREVIEW_FPS = 30  # 30fps 足够"同步"观感，且给 OCR 线程留出 CPU
OCR_ANSWER_COLOR = "#ff4040"

# 活动模式：科举=文字题走题库匹配；看图说话=图标 dHash 走图标库匹配
ACTIVITIES = {"keju": "科举文字题", "picture": "看图说话"}
_PICTURE_DEFAULT = {  # 看图说话默认 ROI（1024x768 布局：居中技能图标本体 + 下方四选项）
    "icon_roi": {"x": 43.5, "y": 36.5, "w": 13.0, "h": 13.0},
    "option_roi": {"x": 25.0, "y": 60.0, "w": 55.0, "h": 18.0},
}


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


def _icon_hash(img: Image.Image) -> str:
    """图标 256 位哈希（17x16 梯度）：比 8x8 dHash 细节多一个数量级，
    用于看图说话的图标库匹配（同图标渲染一致距离为 0，不同图标距离远大于阈值）。"""
    g = img.convert("L").resize((17, 16), Image.BILINEAR)
    px = list(g.getdata())
    bits = 0
    for y in range(16):
        row = y * 17
        for x in range(16):
            bits = (bits << 1) | int(px[row + x] < px[row + x + 1])
    return f"{bits:064x}"


class Viewer(tk.Tk):
    """窗口 2：预览 + ROI + 答案红框 + 录入。"""

    def __init__(self, cfg: dict, bank: matcher.QuestionBank | None, bank_path: str = "questions.json"):
        super().__init__()
        self.title("答题识别窗口")
        self.cfg = cfg
        self.bank = bank
        self.bank_path = bank_path
        self._icons_path = "icons.json"
        try:
            self._icons = matcher.IconBank.load(self._icons_path)
        except Exception:
            self._icons = matcher.IconBank([])
        self._last_icon_hash: int | None = None
        self._activity = cfg.get("activity", "keju")
        if self._activity not in ACTIVITIES:
            self._activity = "keju"
        self._result_queue: queue.Queue = queue.Queue()
        self._preview_queue: queue.Queue = queue.Queue(maxsize=1)  # 只留最新帧，避免预览滞后
        self._running = False
        self._generation = 0  # 线程代际：停止+再启动时递增，让旧线程及时退出
        self._threads: list[threading.Thread] = []
        self._ocr_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

        self._source = tk.StringVar()
        # 绿框=题目区(科举)或图标区(看图说话)、蓝框=选项区:与识别实际使用的 ROI 同源,拖拽实时生效
        pic = dict(cfg.get("picture", _PICTURE_DEFAULT), **{
            k: v for k, v in _PICTURE_DEFAULT.items() if k not in cfg.get("picture", {})
        })
        self._picture_rois = (dict(pic["icon_roi"]), dict(pic["option_roi"]))
        self._keju_rois = (
            dict(cfg.get("question_roi", {"x": 10, "y": 10, "w": 80, "h": 30})),
            dict(cfg.get("option_roi", {"x": 40.0, "y": 47.0, "w": 20.0, "h": 20.0})),
        )
        q0, o0 = self._picture_rois if self._activity == "picture" else self._keju_rois
        self._roi = dict(q0)
        self._option_roi = dict(o0)
        self._img: Image.Image | None = None
        self._full_size: tuple[int, int] | None = None  # 原始截图尺寸（OCR 坐标基准）
        # canvas item 常驻复用：每帧只更新图像与坐标，不 delete/all 重建（Tk 重建开销大）
        self._img_item = None
        self._q_roi_item = None  # 题目区绿框
        self._o_roi_item = None  # 选项区蓝框
        self._ans_item = None  # 答案红框（复用，避免每帧新建 item 泄漏）
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
        ttk.Label(top, text="活动:").pack(side="left")
        self._activity_box = ttk.Combobox(
            top, state="readonly", width=10, values=list(ACTIVITIES.values())
        )
        self._activity_box.current(list(ACTIVITIES).index(self._activity))
        self._activity_box.pack(side="left", padx=(6, 14))
        self._activity_box.bind("<<ComboboxSelected>>", self._on_activity_changed)
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

    # ---- 活动切换：科举(题库文字匹配) / 看图说话(图标哈希匹配) ----
    def _on_activity_changed(self, _event) -> None:
        names = list(ACTIVITIES)
        self._activity = names[self._activity_box.current()]
        q0, o0 = self._picture_rois if self._activity == "picture" else self._keju_rois
        self._roi = dict(q0)
        self._option_roi = dict(o0)
        self._last_icon_hash = None
        self._draw_roi()
        self._update_roi_label()

    # ---- 来源管理 ----
    def _reload_sources(self) -> None:
        self._sources = screen.list_sources()
        names = [s.name for s in self._sources]
        self._source_box["values"] = names
        if not names:
            return
        # 配置了窗口关键词时自动选中匹配窗口，否则取第一个窗口源
        keyword = self.cfg.get("window_keyword", "")
        idx = 0
        if keyword:
            hit = next(
                (i for i, s in enumerate(self._sources)
                 if s.kind == "window" and keyword in s.name),
                None,
            )
            if hit is not None:
                idx = hit
        else:
            win_idx = next(
                (i for i, s in enumerate(self._sources) if s.kind == "window"),
                None,
            )
            if win_idx is not None:
                idx = win_idx
        self._source_box.current(idx)

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
        photo = ImageTk.PhotoImage(img)
        self._photo = photo
        cx, cy = ox + disp_w // 2, oy + disp_h // 2
        if self._img_item is None:
            self._img_item = self._canvas.create_image(cx, cy, image=photo, anchor="center")
        else:
            self._canvas.itemconfigure(self._img_item, image=photo)
            self._canvas.coords(self._img_item, cx, cy)
        self._draw_roi()
        self._draw_answer_box()

    def _img_to_canvas(self, x: float, y: float) -> tuple[float, float]:
        ox, oy = self._offset
        return ox + x * self._scale, oy + y * self._scale

    def _draw_roi(self) -> None:
        if self._img is None:
            return
        w, h = self._img.size
        # 题目区（绿）+ 选项区（蓝），写死布局便于核对；canvas item 复用只更新坐标
        for attr, roi, color in (
            ("_q_roi_item", self._roi, "#00ff00"),
            ("_o_roi_item", self._option_roi, "#00aaff"),
        ):
            rx, ry = roi["x"] / 100 * w, roi["y"] / 100 * h
            rw, rh = roi["w"] / 100 * w, roi["h"] / 100 * h
            x1, y1 = self._img_to_canvas(rx, ry)
            x2, y2 = self._img_to_canvas(rx + rw, ry + rh)
            item = getattr(self, attr)
            if item is None:
                setattr(
                    self, attr,
                    self._canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=2, tags="roi"),
                )
            else:
                self._canvas.coords(item, x1, y1, x2, y2)

    def _draw_answer_box(self) -> None:
        if self._img is None or self._answer_line is None or self._full_size is None:
            # 无答案时隐藏红框（item 复用，不删除重建）
            if self._ans_item is not None:
                self._canvas.itemconfigure(self._ans_item, state="hidden")
            return
        line, left, right = self._answer_line
        # 答案行坐标基于“选项区”裁剪图：先换算回原图坐标（加 option_roi 偏移），再换算到显示图坐标
        fw, fh = self._full_size
        ratio_x = self._img.width / fw
        ratio_y = self._img.height / fh
        roi_x = fw * self._option_roi["x"] / 100
        roi_y = fh * self._option_roi["y"] / 100
        ax = (roi_x + line.center_x) * ratio_x
        ay = (roi_y + line.center_y) * ratio_y
        half_w = line.width / 2 * ratio_x
        x1, y1 = self._img_to_canvas(ax - half_w + line.width * left * ratio_x, ay - line.height / 2 * ratio_y)
        x2, y2 = self._img_to_canvas(ax - half_w + line.width * right * ratio_x, ay + line.height / 2 * ratio_y)
        if self._ans_item is None:
            self._ans_item = self._canvas.create_rectangle(
                x1, y1, x2, y2, outline=OCR_ANSWER_COLOR, width=3
            )
        else:
            self._canvas.coords(self._ans_item, x1, y1, x2, y2)
            self._canvas.itemconfigure(self._ans_item, state="normal")

    @staticmethod
    def _strip_question_prefix(text: str) -> str:
        """去掉“御前科举大赛第X关…题目：”等关卡前缀，只留题目正文（用于匹配）。"""
        m = re.search(r"题目[:：]\s*", text)
        if m:
            return text[m.end():]
        return text

    _LEVEL_CUT_RE = re.compile(r"御前科举|第[一二三四五六七八九十百\d]+关\s*[:：]|这一关考的是")

    @classmethod
    def _clean_question(cls, text: str) -> list[str]:
        """把一行/整段文本清理成候选题目片段。

        OCR 常把关卡说明行与题目正文合并进同一检测框，且“题目：”可能出现
        在框内任意位置。因此用两种顺序各清理一次：
        - 先砍关卡词再截“题目：”（“题目：”在行首/中部时有效）
        - 先截“题目：”再砍关卡词（“题目：”在行尾时有效，如“…题目：茅台酒属于”）
        """
        out: list[str] = []
        for t in (
            cls._strip_question_prefix(re.split(cls._LEVEL_CUT_RE, text)[0]),
            re.split(cls._LEVEL_CUT_RE, cls._strip_question_prefix(text))[0],
        ):
            t = t.strip().strip("，。；：、")
            if len(t) >= 4 and t not in out:
                out.append(t)
        return out

    def _match_question(self, joined: str, lines: list[ocr.Line]):
        """题目匹配：整段优先，逐行兜底（每段按两种清理顺序生成候选）。"""
        for cand in [joined] + [ln.text for ln in lines]:
            for t in self._clean_question(cand):
                q = self.bank.match(t)
                if q:
                    return q
        return None

    @staticmethod
    def _is_ui_noise(text: str) -> bool:
        """系统 UI 噪声行：标题、按钮、进度提示、关卡提示等，不影响识别结果。

        注意：含 "题目：" 的行是题目正文的一部分，即使带关卡前缀也不过滤。
        """
        t = text.strip()
        if len(t) <= 1:  # 如 "问" 按钮
            return True
        if "题目：" in t:
            return False
        if re.search(
            r"离开答题|当前第\s*\d|还可以答|附加考题?|附加题|第\d+题"
            r"|连对|科举大赛第?\s*\d*\s*关|这一关考的是|殿试部分"
            r"|[吏户礼兵刑工]部考题|已答\d+题|答对\d+题",
            t,
        ):
            return True
        return False

    # ---- ROI 拖拽（题目区绿框 + 选项区蓝框均可拖动/缩放，空白处拖出新题目框） ----
    def _to_img_coord(self, cx: float, cy: float) -> tuple[float, float]:
        ox, oy = self._offset
        return (cx - ox) / self._scale, (cy - oy) / self._scale

    def _on_press(self, event) -> None:
        if self._img is None:
            return
        ix, iy = self._to_img_coord(event.x, event.y)
        w, h = self._img.size
        # 命中哪个框就拖哪个（选项框判定在前：两框相邻时优先响应更小的选项框）
        for target, roi in (("o", self._option_roi), ("q", self._roi)):
            rx = roi["x"] / 100 * w
            ry = roi["y"] / 100 * h
            rw = roi["w"] / 100 * w
            rh = roi["h"] / 100 * h
            if rx <= ix <= rx + rw and ry <= iy <= ry + rh:
                on_handle = ix > rx + rw - 14 and iy > ry + rh - 14
                self._drag = {
                    "start": (ix, iy),
                    "orig": (rx, ry, rw, rh),
                    "target": target,
                    "mode": "resize" if on_handle else "move",
                }
                return
        # 空白处按下：拖出一个新的题目框
        self._drag = {"start": (ix, iy), "orig": (0, 0, 0, 0), "target": "q", "mode": "create"}

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
        roi = {"x": nx / w * 100, "y": ny / h * 100, "w": nw / w * 100, "h": nh / h * 100}
        if self._drag["target"] == "o":
            self._option_roi = roi
        else:
            self._roi = roi
        self._draw_roi()
        self._draw_answer_box()
        self._update_roi_label()

    def _on_release(self, _event) -> None:
        self._drag = None

    def _reset_roi(self) -> None:
        self._roi = dict(self.cfg.get("question_roi", {"x": 10, "y": 10, "w": 80, "h": 30}))
        self._option_roi = dict(
            self.cfg.get("option_roi", {"x": 40.0, "y": 47.0, "w": 20.0, "h": 20.0})
        )
        self._draw_roi()
        self._update_roi_label()

    def _update_roi_label(self) -> None:
        self._roi_var.set(
            f"题目ROI: x={self._roi['x']:.1f}% y={self._roi['y']:.1f}% "
            f"w={self._roi['w']:.1f}% h={self._roi['h']:.1f}%  "
            f"选项ROI: x={self._option_roi['x']:.1f}% y={self._option_roi['y']:.1f}% "
            f"w={self._option_roi['w']:.1f}% h={self._option_roi['h']:.1f}%"
        )

    # ---- 运行控制 ----
    def _toggle(self) -> None:
        if self._running:
            self._running = False
            self._generation += 1  # 使旧线程下一轮循环退出
            self._start_btn.config(text="开始")
            return
        source = self._current_source()
        if source is None:
            return
        self._running = True
        self._start_btn.config(text="停止")
        self._start_threads(source)

    def _start_threads(self, source: screen.Source) -> None:
        generation = self._generation

        def alive() -> bool:
            return self._running and generation == self._generation

        def preview_loop() -> None:
            period = 1.0 / PREVIEW_FPS
            while alive():
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
            interval = self.cfg.get("interval_sec", 0.05)
            last_key: tuple | None = None
            last_hash: int | None = None
            # 引擎预热：模型加载与首次推理较慢（秒级），点「开始」时先跑空图完成，
            # 避免第一道题多等数秒。预热失败不打断，首次真实识别会走正常错误提示。
            try:
                blank = Image.new("RGB", (64, 16), "white")
                mt = ocr_cfg.get("model_type", "tiny")
                lang = ocr_cfg.get("lang", "ch")
                dml = ocr_cfg.get("use_dml", False)
                ocr.recognize(blank, lang, 0.6, mt, False, dml)
                ocr.recognize(blank, lang, 0.6, mt, True, dml)
            except Exception:
                pass
            while alive():
                time.sleep(interval)
                try:
                    # ROI 取 UI 当前值：预览里拖拽题目/选项框立即对识别生效
                    img, _ = screen.capture(source)
                    q_crop = screen.crop_region(img, self._roi)
                    o_crop = screen.crop_region(img, self._option_roi)
                except Exception as exc:
                    self._result_queue.put(("error", f"截图失败: {exc}"))
                    continue
                cur_hash = _dhash(q_crop)
                if cur_hash == last_hash:
                    continue
                last_hash = cur_hash
                try:
                    mt = ocr_cfg.get("model_type", "tiny")
                    lang = ocr_cfg.get("lang", "ch")
                    conf = ocr_cfg.get("confidence", 0.6)
                    dml = ocr_cfg.get("use_dml", False)
                    if self._activity == "picture":
                        # 看图说话：图标哈希定答案，选项区 OCR 仅用于红框定位
                        ih = _icon_hash(q_crop)
                        self._last_icon_hash = ih
                        answer = self._icons.match(ih) if self._icons else None
                        fo = self._ocr_executor.submit(ocr.recognize, o_crop, lang, conf, mt, True, dml)
                        o_lines = [ln for ln in fo.result() if not self._is_ui_noise(ln.text)]
                        answer_line = self._find_answer_line(o_lines, answer) if answer else None
                        self._result_queue.put((
                            "result", o_lines,
                            {"question": f"看图识别: {answer}" if answer else "看图识别: 图标未收录,请在下方录入答案"},
                            answer or "", answer_line,
                        ))
                        continue
                    # 题目/选项双引擎并行识别（第二个引擎实例互不阻塞）
                    fq = self._ocr_executor.submit(ocr.recognize, q_crop, lang, conf, mt, False, dml)
                    fo = self._ocr_executor.submit(ocr.recognize, o_crop, lang, conf, mt, True, dml)
                    q_lines = fq.result()
                    o_lines = fo.result()
                except Exception as exc:
                    self._result_queue.put(("error", f"识别失败: {exc}"))
                    continue
                # 剔除系统 UI 噪声行（标题、按钮、进度提示等），只留题目与选项
                q_lines = [ln for ln in q_lines if not self._is_ui_noise(ln.text)]
                o_lines = [ln for ln in o_lines if not self._is_ui_noise(ln.text)]
                if not q_lines or not o_lines:
                    continue
                key = tuple(ln.text for ln in q_lines[:2])
                if key == last_key:
                    continue
                last_key = key
                # 题目匹配：题目区多行按 y 排序拼接（题目常折行显示），多策略清理后匹配
                q_lines.sort(key=lambda ln: ln.center_y)
                main_text = "".join(ln.text for ln in q_lines)
                question = self._match_question(main_text, q_lines) if self.bank else None
                answer = question.get("answer", "") if question else ""
                # 答案行定位：只在选项区内找，答案命中段直接给真实坐标
                answer_line = self._find_answer_line(o_lines, answer) if answer else None
                self._result_queue.put(("result", q_lines + o_lines, question, answer, answer_line))

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
                    left, right = Viewer._segment_bounds(ln, part)
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

    @staticmethod
    def _segment_bounds(line: ocr.Line, part: str) -> tuple[float, float]:
        """在行内定位答案所在 OCR 段（选项文本框）的水平占比。

        OCR 常把选项拆成多个框且丢失 "A、" 前缀（如《石壕吏》B《长安吏》），
        因此：先找单段命中；未命中再把相邻段拼起来，取覆盖答案的最窄范围。
        无段信息时退化为字符比例。
        """
        if line.segments:
            n = len(line.segments)
            # 1) 单段命中优先
            for seg_text, seg_left, seg_right in line.segments:
                if part in seg_text or seg_text in part:
                    return seg_left, seg_right
            # 2) 跨段拼接兜底：答案可能被前缀/相邻框拆开，取最窄覆盖范围
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
            return idx / max(len(line.text), 1), (idx + len(part)) / max(len(line.text), 1)
        return 0.0, 1.0

    # ---- 答案录入（收录到题库 / 图标库） ----
    def _add_answer(self) -> None:
        text = self._entry_var.get().strip()
        if not text:
            return
        if self._activity == "picture" and self._last_icon_hash is not None:
            # 看图说话：答案连同当前图标哈希写入 icons.json
            if self._icons is not None:
                self._icons.add(self._last_icon_hash, text)
                try:
                    self._icons.save(self._icons_path)
                except OSError as exc:
                    self._set_text(self._a_text, f"写入图标库失败: {exc}")
                    return
            self._set_text(self._a_text, f"已收录图标: {text}（{len(self._icons or [])} 个）")
            self._entry_var.set("")
            return
        if not self._last_question:
            return
        if self.bank is not None:
            self.bank.add(self._last_question, text)
        try:
            with open(self.bank_path, encoding="utf-8-sig") as f:
                data = json.load(f)
            hit = next((item for item in data if item.get("question") == self._last_question), None)
            if hit is None:
                data.append({"id": len(data) + 1, "question": self._last_question, "options": [], "answer": text})
            else:
                hit["answer"] = text  # 题目已存在：用新答案覆盖旧答案
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
                    # 题目栏显示题库命中的原文（干净无"御前科举大赛第X关"等前缀）；
                    # 未命中则显示全部识别文本（OCR 常把一行拆成多段，只看第一行会断）
                    q_display = question.get("question", "") if question else "".join(
                        ln.text for ln in lines
                    )
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
        self._ocr_executor.shutdown(wait=False)
        self.destroy()
