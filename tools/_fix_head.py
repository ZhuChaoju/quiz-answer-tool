# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"src\quiz_answer_tool\activities\text.py"
s = open(p, encoding="utf-8").read()
old = """    def recognize(self, frame: Image.Image, ocr_cfg: dict[str, Any]) -> ModuleResult:
        res = ModuleResult()
        roi_q, roi_o = self.rois["question"], self.rois["option"]
        mt = ocr_cfg.get("model_type", "tiny")"""
new = """    def recognize(self, frame: Image.Image, ocr_cfg: dict[str, Any]) -> ModuleResult:
        res = ModuleResult()
        roi_q, roi_o = self.rois["question"], self.rois["option"]
        # 廉价预检：题面区亮度低于模块校准阈值（presence_min_lum，乡试实测
        # 无框 78 / 有框 102 → 阈值 88）判定无题目，整轮跳过全部 OCR
        min_lum = float(getattr(self, "presence_min_lum", 0) or 0)
        if min_lum > 0:
            import numpy as _np

            region = _np.asarray(roi_q.crop(frame).convert("L"), dtype=_np.float64)
            if region.mean() < min_lum:
                res.state = "no_dialog"
                res.note = f"识别区域无题目（亮度 {region.mean():.0f} < {min_lum}）"
                return res
        mt = ocr_cfg.get("model_type", "tiny")"""
assert old in s, "recognize head pattern"
s = s.replace(old, new, 1)
ast.parse(s)
open(p, "w", encoding="utf-8").write(s)
print("presence pre-check wired, syntax ok")
