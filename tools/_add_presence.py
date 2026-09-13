# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"src\quiz_answer_tool\activities\text.py"
s = open(p, encoding="utf-8").read()
old = """        # 廉价预检：答题框是亮色面板（亮度高），无题目时该区域是暗色游戏场景——
        # 直接跳过全部 OCR，避免刷怪/战斗画面的动画触发无意义识别
        import numpy as _np

        region = _np.asarray(
            roi_q.crop(frame).convert("L"), dtype=_np.float64
        )
        if region.mean() < 150:
            res.state = "no_dialog"
            res.note = "识别区域无题目（区域亮度过低）"
            return res
        q_crop = roi_q.crop(frame, pad=0.02)
        o_crop = roi_o.crop(frame, pad=0.02)
        mt = ocr_cfg.get("model_type", "tiny")"""
new = """        # 廉价预检：题面区亮度低于模块校准阈值（presence_min_lum，乡试实测
        # 无框 78 / 有框 102 → 阈值 88）时判定无题目，整轮跳过全部 OCR。
        import numpy as _np

        min_lum = float(getattr(self, "presence_min_lum", 0) or 0)
        if min_lum > 0:
            region = _np.asarray(roi_q.crop(frame).convert("L"), dtype=_np.float64)
            if region.mean() < min_lum:
                res.state = "no_dialog"
                res.note = f"识别区域无题目（亮度 {region.mean():.0f} < {min_lum}）"
                return res
        q_crop = roi_q.crop(frame, pad=0.02)
        o_crop = roi_o.crop(frame, pad=0.02)
        mt = ocr_cfg.get("model_type", "tiny")"""
assert old in s, "text pre-check pattern"
s = s.replace(old, new, 1)
ast.parse(s)
open(p, "w", encoding="utf-8").write(s)
print("text presence pre-check (per-module threshold) ok")

# ---- base.py: 装配 presence_min_lum ----
p2 = r"src\quiz_answer_tool\activities\base.py"
s2 = open(p2, encoding="utf-8").read()
old2 = """        # OCR 行折行合并阈值（相对行高）；科举折行题面 0.6，可按模块配置覆盖
        self.merge_threshold = float(data.get("merge_threshold", 0.6))"""
new2 = """        # OCR 行折行合并阈值（相对行高）；科举折行题面 0.6，可按模块配置覆盖
        self.merge_threshold = float(data.get("merge_threshold", 0.6))
        # 廉价预检阈值：题面区平均亮度低于该值判定无题目（0=禁用）
        self.presence_min_lum = float(data.get("presence_min_lum", 0) or 0)"""
assert old2 in s2, "base pattern"
s2 = s2.replace(old2, new2, 1)
ast.parse(s2)
open(p2, "w", encoding="utf-8").write(s2)
print("base.py presence_min_lum ok")
