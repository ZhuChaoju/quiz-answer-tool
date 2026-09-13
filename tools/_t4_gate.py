# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ---- 任务4: 题面关键词闸门（文字模块）+ 模块配置 ----
p = r"src\quiz_answer_tool\activities\text.py"
s = open(p, encoding="utf-8").read()

old = """    # ---- 识别 ----
    def recognize(self, frame: Image.Image, ocr_cfg: dict[str, Any]) -> ModuleResult:
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
new = """    # ---- 识别 ----
    def recognize(self, frame: Image.Image, ocr_cfg: dict[str, Any]) -> ModuleResult:
        res = ModuleResult()
        roi_q, roi_o = self.rois["question"], self.rois["option"]
        mt = ocr_cfg.get("model_type", "tiny")
        lang = ocr_cfg.get("lang", "ch")
        conf = float(ocr_cfg.get("confidence", 0.4))
        dml = bool(ocr_cfg.get("use_dml", False))
        th = self.merge_threshold
        if self.roi_variants:
            # 多布局变体：逐变体 OCR 题面区，选题面文字最多的那套布局
            best_chars, best_q, best_o, best_raw = -1, None, None, ""
            for rv in self.roi_variants:
                qc = rv["question"].crop(frame, pad=0.02)
                ls_q = ocr.recognize(qc, lang, max(conf, 0.3), mt, False, dml, th)
                raw = "".join(ln.text for ln in ls_q)
                kept = [ln for ln in ls_q if not self.is_noise(ln.text)]
                chars = sum(len(ln.text) for ln in kept)
                if chars > best_chars:
                    best_chars, best_q, best_o, best_raw = chars, qc, rv["option"].crop(frame, pad=0.02), raw
            q_crop, o_crop = best_q, best_o
            raw_all = best_raw
        else:
            q_crop = roi_q.crop(frame, pad=0.02)
            o_crop = roi_o.crop(frame, pad=0.02)
            ls_q = ocr.recognize(q_crop, lang, conf, mt, False, dml, th)
            raw_all = "".join(ln.text for ln in ls_q)
        # 关键词闸门：题面区没有本活动的题目关键词 → 无题目，跳过选项 OCR 与匹配
        if self.gate_keywords and not any(k in raw_all for k in self.gate_keywords):
            res.state = "no_dialog"
            res.note = "未检测到题目关键词"
            return res
        q_lines = [
            ln for ln in ocr.recognize(q_crop, lang, conf, mt, False, dml, th)
            if not self.is_noise(ln.text)
        ]"""
assert old in s, "text recognize pattern"
s = s.replace(old, new, 1)

# gate_keywords 装配
old2 = """        mod._config_path = (
            os.path.join(bank_dir, "modules", f"{mod.id}.json")
            if os.path.isdir(os.path.join(bank_dir, "modules"))
            else os.path.join(bank_dir, "module.json")
        )
        return mod"""
new2 = """        mod.gate_keywords: list = list(data.get("gate_keywords", []))
        mod._config_path = (
            os.path.join(bank_dir, "modules", f"{mod.id}.json")
            if os.path.isdir(os.path.join(bank_dir, "modules"))
            else os.path.join(bank_dir, "module.json")
        )
        return mod"""
assert old2 in s, "gate_keywords init pattern"
s = s.replace(old2, new2, 1)
ast.parse(s)
open(p, "w", encoding="utf-8").write(s)
print("text.py keyword gate ok")
