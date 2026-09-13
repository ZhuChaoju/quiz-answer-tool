# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"src\quiz_answer_tool\activities\icon.py"
s = open(p, encoding="utf-8").read()

old = """        if box:
            self.last_box = box
            icon_crop = frame.crop(box)
        else:
            self.last_box = None
            icon_crop = roi_icon.crop(frame)"""
new = """        if box:
            self.last_box = box
            icon_crop = frame.crop(box)
        else:
            self.last_box = None
            icon_crop = roi_icon.crop(frame)
        # 选项区：图标定位成功时按固定偏移跟随（整框拖动场景）；否则退回百分比 ROI
        if box:
            orect = self._option_rect_follow(frame, box)
            res.option_rect = orect
            o_crop = frame.crop(orect)
        else:
            orect = roi_o.rect_px(frame.size, 0.02)
            res.option_rect = tuple(int(v) for v in orect)
            o_crop = frame.crop((int(orect[0]), int(orect[1]), int(orect[2]), int(orect[3])))"""
assert old in s, "icon crop pattern"
s = s.replace(old, new, 1)
print("icon crop follow ok")
