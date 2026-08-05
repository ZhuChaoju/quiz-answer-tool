"""主流程：截图 → OCR → 匹配 → 定位选项 → 点击。"""

from __future__ import annotations

import logging
import threading
import time

import keyboard

from . import actuator, capture, matcher, ocr

log = logging.getLogger("quiz_answer_tool")


def _find_option_line(lines: list[ocr.Line], answer: str) -> ocr.Line | None:
    """在选项行中定位答案所在行：前缀字母匹配优先，其次模糊匹配文本。"""
    answer_letter = answer.strip().upper()
    answer_text = None
    for ln in lines:
        first = ln.text.strip()[:1].upper()
        if first == answer_letter:
            return ln
        if answer_letter in ln.text.upper():
            return ln
    for ln in lines:
        if answer_text and answer_text in ln.text:
            return ln
    return None


class Pipeline:
    def __init__(self, cfg: dict, dry_run: bool = False):
        self.cfg = cfg
        self.dry_run = dry_run
        self.enabled = False
        self._stop = threading.Event()
        self.bank: matcher.QuestionBank | None = None

    def run(self, hwnd: int) -> None:
        """主循环；按 hotkey 切换启停。"""
        hotkey = self.cfg.get("hotkey", "f8")
        keyboard.add_hotkey(hotkey, self._toggle)
        log.info("pipeline started, hotkey=%s", hotkey)
        try:
            while not self._stop.is_set():
                if self.enabled:
                    self._step(hwnd)
                time.sleep(self.cfg.get("interval_sec", 0.5))
        finally:
            keyboard.remove_hotkey(hotkey)

    def stop(self) -> None:
        self._stop.set()

    def _toggle(self) -> None:
        self.enabled = not self.enabled
        log.info("enabled=%s", self.enabled)

    def _step(self, hwnd: int) -> None:
        if self.bank is None:
            return
        ocr_cfg = self.cfg.get("ocr", {})
        q_img = capture.capture_region(hwnd, self.cfg["region_question"])
        lines = ocr.recognize(q_img, ocr_cfg.get("lang", "ch"), ocr_cfg.get("confidence", 0.6))
        if not lines:
            return
        question_text = lines[0].text
        question = self.bank.match(question_text)
        if question is None:
            log.info("no match: %s", question_text)
            return
        log.info("matched #%s: %s -> %s", question.get("id"), question_text, question.get("answer"))
        opt_img = capture.capture_region(hwnd, self.cfg["region_options"])
        opt_lines = ocr.recognize(opt_img, ocr_cfg.get("lang", "ch"), ocr_cfg.get("confidence", 0.6))
        target = _find_option_line(opt_lines, question.get("answer", ""))
        if target is None:
            log.warning("option not found for answer %s", question.get("answer"))
            return
        img_w, img_h = opt_img.size
        x_pct = target.center_x / img_w * 100
        y_pct = target.center_y / img_h * 100
        actuator.click_relative(hwnd, x_pct, y_pct, dry_run=self.dry_run)
        log.info("clicked at %.1f%%, %.1f%%", x_pct, y_pct)
