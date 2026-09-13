# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ---- text.py: 识别时按变体探测题面文字量，选最优布局 ----
p = r"src\quiz_answer_tool\activities\text.py"
s = open(p, encoding="utf-8").read()

old = """    # ---- 识别 ----
    def recognize(self, frame: Image.Image, ocr_cfg: dict[str, Any]) -> ModuleResult:
        res = ModuleResult()
        roi_q, roi_o = self.rois["question"], self.rois["option"]
        q_crop = roi_q.crop(frame, pad=0.02)
        o_crop = roi_o.crop(frame, pad=0.02)
        mt = ocr_cfg.get("model_type", "tiny")
        lang = ocr_cfg.get("lang", "ch")
        conf = float(ocr_cfg.get("confidence", 0.4))
        dml = bool(ocr_cfg.get("use_dml", False))
        # 选项区用第二引擎实例并行识别（端到端延迟 ≈ max(题目, 选项)，~200ms 量级）
        fo = _OCR_EXECUTOR.submit(
            ocr.recognize, o_crop, lang, conf, mt, True, dml, self.merge_threshold
        )
        q_lines = [
            ln
            for ln in ocr.recognize(q_crop, lang, conf, mt, False, dml, self.merge_threshold)
            if not self.is_noise(ln.text)
        ]"""
new = """    # ---- 识别 ----
    def _choose_variant(self, frame: Image.Image, ocr_cfg: dict[str, Any]):
        \"\"\"多布局变体：逐变体 OCR 题面区，选题面文字最多的那套（返回题面/选项裁剪与行）。\"\"\"
        mt = ocr_cfg.get("model_type", "tiny")
        lang = ocr_cfg.get("lang", "ch")
        conf = float(ocr_cfg.get("confidence", 0.4))
        dml = bool(ocr_cfg.get("use_dml", False))
        th = self.merge_threshold
        best = None
        for rv in self.roi_variants or []:
            q_crop = rv["question"].crop(frame, pad=0.02)
            lines_q = [
                ln for ln in ocr.recognize(q_crop, lang, max(conf, 0.3), mt, False, dml, th)
                if not self.is_noise(ln.text)
            ]
            chars = sum(len(ln.text) for ln in lines_q)
            if best is None or chars > best[0]:
                best = (chars, rv, q_crop, lines_q)
        if best is None:
            q_crop = self.rois["question"].crop(frame, pad=0.02)
            return q_crop, self.rois["option"].crop(frame, pad=0.02), [
                ln for ln in ocr.recognize(q_crop, lang, conf, mt, False, dml, th)
                if not self.is_noise(ln.text)
            ], th
        chars, rv, q_crop, lines_q = best
        return q_crop, rv["option"].crop(frame, pad=0.02), lines_q, th

    # ---- 识别 ----
    def recognize(self, frame: Image.Image, ocr_cfg: dict[str, Any]) -> ModuleResult:
        res = ModuleResult()
        roi_q, roi_o = self.rois["question"], self.rois["option"]
        mt = ocr_cfg.get("model_type", "tiny")
        lang = ocr_cfg.get("lang", "ch")
        conf = float(ocr_cfg.get("confidence", 0.4))
        dml = bool(ocr_cfg.get("use_dml", False))
        if self.roi_variants:
            q_crop, o_crop, q_lines, th = self._choose_variant(frame, ocr_cfg)
        else:
            q_crop = roi_q.crop(frame, pad=0.02)
            o_crop = roi_o.crop(frame, pad=0.02)
            th = self.merge_threshold
        # 选项区用第二引擎实例并行识别（端到端延迟 ≈ max(题目, 选项)，~200ms 量级）
        fo = _OCR_EXECUTOR.submit(ocr.recognize, o_crop, lang, conf, mt, True, dml, th)
        q_lines = [ln for ln in q_lines if not self.is_noise(ln.text)]
        # 选项区只剔除空行：科举选项常为单字（金/木/水/火），不能套用题目区的短行噪声规则
        o_lines = [ln for ln in fo.result() if ln.text.strip()]
        res.lines = q_lines + o_lines
        if not q_lines or not o_lines:
            res.state = "no_dialog"
            res.note = "识别区域内容不足"
            return res"""
assert old in s, "text recognize pattern"
s = s.replace(old, new, 1)
ast.parse(s)
open(p, "w", encoding="utf-8").write(s)
print("text.py variants ok")
