# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ---- base.py: 装配 roi_variants ----
p = r"src\quiz_answer_tool\activities\base.py"
s = open(p, encoding="utf-8").read()
old = """        roi_data = data.get("roi") or {}
        self.rois = {k: Roi.from_json(roi_data.get(k)) for k in self.ROI_KEYS}
        # OCR 行折行合并阈值（相对行高）；科举折行题面 0.6，可按模块配置覆盖
        self.merge_threshold = float(data.get("merge_threshold", 0.6))"""
new = """        roi_data = data.get("roi") or {}
        self.rois = {k: Roi.from_json(roi_data.get(k)) for k in self.ROI_KEYS}
        # 可选布局变体（如同一会试的有图/无图两种排版）：识别时逐变体探测题面文字量，
        # 选文字最多的那套生效。结构: [{"question":{...},"option":{...}}, ...]
        self.roi_variants: list[dict[str, Roi]] = []
        for vset in data.get("roi_variants") or []:
            if isinstance(vset, dict):
                self.roi_variants.append(
                    {k: Roi.from_json(v) for k, v in vset.items() if isinstance(v, dict)}
                )
        # OCR 行折行合并阈值（相对行高）；科举折行题面 0.6，可按模块配置覆盖
        self.merge_threshold = float(data.get("merge_threshold", 0.6))"""
assert old in s, "base pattern"
s = s.replace(old, new, 1)
ast.parse(s)
open(p, "w", encoding="utf-8").write(s)
print("base.py roi_variants ok")
