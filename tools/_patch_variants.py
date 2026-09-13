# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ---- 补丁 1: text.py 变体选择 ----
p1 = r"src\quiz_answer_tool\activities\text.py"
s1 = open(p1, encoding="utf-8").read()
old1 = """    def recognize(self, frame: Image.Image, ocr_cfg: dict[str, Any]) -> ModuleResult:
        res = ModuleResult()
        roi_q, roi_o = self.rois["question"], self.rois["option"]
        q_crop = roi_q.crop(frame, pad=0.02)
        o_crop = roi_o.crop(frame, pad=0.02)
        mt = ocr_cfg.get("model_type", "tiny")
        lang = ocr_cfg.get("lang", "ch")
        conf = float(ocr_cfg.get("confidence", 0.4))
        dml = bool(ocr_cfg.get("use_dml", False))
        # 选项区用第二引擎实例并行识别（端到端延迟 ≈ max(题目, 选项)，~200ms 量级）
        fo = _OCR_EXECUTOR.submit(ocr.recognize, o_crop, lang, conf, mt, True, dml, self.merge_threshold)
        q_lines = [
            ln for ln in ocr.recognize(q_crop, lang, conf, mt, False, dml, self.merge_threshold)
            if not self.is_noise(ln.text)
        ]"""
new1 = """    def recognize(self, frame: Image.Image, ocr_cfg: dict[str, Any]) -> ModuleResult:
        res = ModuleResult()
        roi_q, roi_o = self.rois["question"], self.rois["option"]
        mt = ocr_cfg.get("model_type", "tiny")
        lang = ocr_cfg.get("lang", "ch")
        conf = float(ocr_cfg.get("confidence", 0.4))
        dml = bool(ocr_cfg.get("use_dml", False))
        th = self.merge_threshold
        if self.roi_variants:
            # 多布局变体：逐变体 OCR 题面区，选题面文字最多的那套布局
            best_chars, best_q, best_o = -1, None, None
            for rv in self.roi_variants:
                qc = rv["question"].crop(frame, pad=0.02)
                ls_q = [
                    ln for ln in ocr.recognize(qc, lang, max(conf, 0.3), mt, False, dml, th)
                    if not self.is_noise(ln.text)
                ]
                chars = sum(len(ln.text) for ln in ls_q)
                if chars > best_chars:
                    best_chars, best_q, best_o = chars, qc, rv["option"].crop(frame, pad=0.02)
            q_crop, o_crop = best_q, best_o
        else:
            q_crop = roi_q.crop(frame, pad=0.02)
            o_crop = roi_o.crop(frame, pad=0.02)
        # 选项区用第二引擎实例并行识别（端到端延迟 ≈ max(题目, 选项)，~200ms 量级）
        fo = _OCR_EXECUTOR.submit(ocr.recognize, o_crop, lang, conf, mt, True, dml, th)
        q_lines = [
            ln for ln in ocr.recognize(q_crop, lang, conf, mt, False, dml, th)
            if not self.is_noise(ln.text)
        ]"""
assert old1 in s1, "text pattern"
s1 = s1.replace(old1, new1, 1)
ast.parse(s1)
open(p1, "w", encoding="utf-8").write(s1)
print("text.py variants ok")

# ---- 补丁 2: viewer.py 闸门覆盖变体 ----
p2 = r"src\quiz_answer_tool\viewer.py"
s2 = open(p2, encoding="utf-8").read()
old2 = """                    gate_main = _dhash(mod.rois[gate_key].crop(frame, pad=0.02))
                    gate_opt = _dhash(mod.rois["option"].crop(frame, pad=0.02))"""
new2 = """                    gate_main = _dhash(mod.rois[gate_key].crop(frame, pad=0.02))
                    gate_opt = _dhash(mod.rois["option"].crop(frame, pad=0.02))
                    gate_parts = [gate_main, gate_opt]
                    for rv in getattr(mod, "roi_variants", []):
                        if "question" in rv:
                            gate_parts.append(_dhash(rv["question"].crop(frame, pad=0.02)))
                    cur = tuple(gate_parts)"""
assert old2 in s2, "viewer pattern"
s2 = s2.replace(old2, new2, 1)
old3 = """                if cur == last_hash:
                    continue
                last_hash = cur
                # 画面已变化：立即清掉上一题的红框/动态选项框，避免新题出来时残留
                self._result_queue.put(("clear",))"""
new3 = """                if cur == last_hash:
                    continue
                # 识别频率上限：动画画面会让闸门频繁变化，全量 OCR 最高 3 次/秒，
                # 防止 CPU 被连续识别打满（0.33s 内的中间变化直接跳过）
                now_t = time.perf_counter()
                if now_t - last_rec_t < 0.33:
                    continue
                last_rec_t = now_t
                last_hash = cur
                # 画面已变化：立即清掉上一题的红框/动态选项框，避免新题出来时残留
                self._result_queue.put(("clear",))"""
assert old3 in s2, "viewer rate pattern"
s2 = s2.replace(old3, new3, 1)
old4 = """            last_hash: int | None = None
            last_mod_id: str | None = None"""
new4 = """            last_hash: tuple | None = None
            last_rec_t = 0.0
            last_mod_id: str | None = None"""
assert old4 in s2, "viewer init pattern"
s2 = s2.replace(old4, new4, 1)
ast.parse(s2)
open(p2, "w", encoding="utf-8").write(s2)
print("viewer gate+ratelimit ok")
