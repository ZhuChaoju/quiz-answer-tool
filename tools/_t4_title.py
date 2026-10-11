# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"src\quiz_answer_tool\activities\text.py"
s = open(p, encoding="utf-8").read()

# 1) 标题闸门：OCR 标题条小区域，确认有活动关键词才继续全量识别
old_gate = """        th = self.merge_threshold
        if self.roi_variants:"""
new_gate = """        th = self.merge_threshold
        # 标题闸门：只 OCR 标题条小区域（~20ms），确认有活动关键词才启动全量识别。
        # 没有题目时几乎零 CPU，比全量 OCR 便宜 20 倍。
        if self.title_keywords:
            title_crop = self.rois["title"].crop(frame, pad=0.05)
            title_raw = "".join(
                ln.text for ln in ocr.recognize(
                    title_crop, lang, 0.3, mt, False, dml, th
                )
            )
            if not any(k in title_raw for k in self.title_keywords):
                res.state = "no_dialog"
                res.note = "标题未命中活动关键词"
                return res
        if self.roi_variants:"""
assert old_gate in s, "gate insert pattern"
s = s.replace(old_gate, new_gate, 1)

# 2) from_json 装配 title_roi / title_keywords
old_init = """        mod.gate_keywords: list = list(data.get("gate_keywords", []))"""
new_init = """        mod.gate_keywords: list = list(data.get("gate_keywords", []))
        mod.title_keywords: list = list(data.get("title_keywords", []))
        if "title" in data.get("roi", {}):
            mod.rois["title"] = Roi.from_json(data["roi"]["title"])
            mod.ROI_KEYS = mod.ROI_KEYS + ("title",)"""
assert old_init in s, "init pattern"
s = s.replace(old_init, new_init, 1)

ast.parse(s)
open(p, "w", encoding="utf-8").write(s)
print("title gate added, syntax ok")
