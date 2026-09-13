# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ---- 补丁 1: text.py 无题目预检 ----
p1 = r"src\quiz_answer_tool\activities\text.py"
s1 = open(p1, encoding="utf-8").read()
old1 = """    # ---- 识别 ----
    def recognize(self, frame: Image.Image, ocr_cfg: dict[str, Any]) -> ModuleResult:
        res = ModuleResult()
        roi_q, roi_o = self.rois["question"], self.rois["option"]
        q_crop = roi_q.crop(frame, pad=0.02)
        o_crop = roi_o.crop(frame, pad=0.02)
        mt = ocr_cfg.get("model_type", "tiny")"""
new1 = """    # ---- 识别 ----
    def recognize(self, frame: Image.Image, ocr_cfg: dict[str, Any]) -> ModuleResult:
        res = ModuleResult()
        roi_q, roi_o = self.rois["question"], self.rois["option"]
        # 廉价预检：答题框是亮色面板（亮度高），无题目时该区域是暗色游戏场景——
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
assert old1 in s1, "text pattern"
s1 = s1.replace(old1, new1, 1)
ast.parse(s1)
open(p1, "w", encoding="utf-8").write(s1)
print("text.py pre-check ok")

# ---- 补丁 2: icon.py 无题目预检 ----
p2 = r"src\quiz_answer_tool\activities\icon.py"
s2 = open(p2, encoding="utf-8").read()
old2 = """        # 1) 图标定位：连通域优先（抗对话框拖动），失败退回固定 ROI
        box = locate_icon(frame, roi_s.__dict__, self.panel_bg) if roi_s.w > 0 else None"""
new2 = """        # 0) 廉价预检：搜索窗平均亮度接近面板底色说明没有答题框，跳过全部计算
        import numpy as _np

        search_crop = roi_s.crop(frame)
        if (
            _np.asarray(search_crop.convert("L"), dtype=_np.float64).mean()
            > sum(self.panel_bg) / 3 + 15
        ) or (
            _np.asarray(search_crop.convert("L"), dtype=_np.float64).mean() < 120
        ):
            res.state = "no_dialog"
            res.note = "识别区域无答题框"
            return res
        # 1) 图标定位：连通域优先（抗对话框拖动），失败退回固定 ROI
        box = locate_icon(frame, roi_s.__dict__, self.panel_bg) if roi_s.w > 0 else None"""
assert old2 in s2, "icon pattern"
s2 = s2.replace(old2, new2, 1)
ast.parse(s2)
open(p2, "w", encoding="utf-8").write(s2)
print("icon.py pre-check ok")

# ---- 补丁 3: 预览帧率 30 → 15 ----
p3 = r"src\quiz_answer_tool\viewer.py"
s3 = open(p3, encoding="utf-8").read()
old3 = "PREVIEW_FPS = 30"
new3 = "PREVIEW_FPS = 15"
assert old3 in s3, "fps pattern"
s3 = s3.replace(old3, new3, 1)
ast.parse(s3)
open(p3, "w", encoding="utf-8").write(s3)
print("preview fps ok")
