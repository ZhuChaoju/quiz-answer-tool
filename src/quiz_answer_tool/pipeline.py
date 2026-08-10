"""识别流水线：实时截屏 → ROI 提取 → OCR → 题库匹配 → 结果供 UI 展示。"""

from __future__ import annotations

import logging
import threading
import time

from . import ocr, screen

log = logging.getLogger("quiz_answer_tool")


def find_answer_line(lines: list[ocr.Line], answer: str) -> ocr.Line | None:
    """在识别行中定位答案所在行：包含关系优先，其次模糊相似。"""
    answer = answer.strip()
    if not answer:
        return None
    for ln in lines:
        text = ln.text.strip()
        if not text:
            continue
        if text == answer or answer in text or text in answer:
            return ln
    from difflib import SequenceMatcher

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


class LivePipeline:
    """后台循环：按间隔抓取来源、裁剪 ROI、OCR、匹配题库，结果回调输出。"""

    def __init__(self, cfg: dict, source: screen.Source, roi: dict):
        self.cfg = cfg
        self.source = source
        self.roi = roi
        self.bank = None
        self._running = False
        self._thread: threading.Thread | None = None

    def set_bank(self, bank) -> None:
        self.bank = bank

    def set_roi(self, roi: dict) -> None:
        self.roi = roi

    def start(self, on_result) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, args=(on_result,), daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    def _loop(self, on_result) -> None:
        ocr_cfg = self.cfg.get("ocr", {})
        interval = self.cfg.get("interval_sec", 1.0)
        last_key: tuple | None = None
        while self._running:
            time.sleep(interval)
            try:
                img, _ = screen.capture(self.source)
                crop = screen.crop_region(img, self.roi)
                lines = ocr.recognize(
                    crop,
                    ocr_cfg.get("lang", "ch"),
                    ocr_cfg.get("confidence", 0.6),
                    ocr_cfg.get("model_type", "tiny"),
                    use_dml=ocr_cfg.get("use_dml", False),
                )
            except Exception as exc:
                log.warning("pipeline step failed: %s", exc)
                continue
            if not lines:
                continue
            key = tuple(ln.text for ln in lines[:2])
            if key == last_key:
                continue
            last_key = key
            question = self.bank.match(lines[0].text) if self.bank else None
            answer = question.get("answer", "") if question else ""
            answer_line = find_answer_line(lines[1:], answer) if answer else None
            on_result(lines, question, answer, answer_line)
