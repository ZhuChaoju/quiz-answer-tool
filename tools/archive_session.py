# -*- coding: utf-8 -*-
"""收尾存档：整屏截图 + 实测关键图，归档到 D:\\work\\实测记录-20260910\\。"""
import os
import shutil

import mss
import mss.tools

OUT = r"D:\work\实测记录-20260910"
os.makedirs(OUT, exist_ok=True)

with mss.mss() as sct:
    mon = sct.monitors[1]
    shot = sct.grab(mon)
    mss.tools.to_png(shot.rgb, shot.size, output=os.path.join(OUT, "桌面最终状态-3840x2160.png"))
    print("full screen saved")

# 本会话实况联调关键图
base = r"D:\work\quiz-answer-tool\build\test_frames"
pairs = [
    (r"D:\work\_downloads\live_calib.png", "校准抓帧-误抓聊天窗口(教训).png"),
    (r"D:\work\_downloads\live_now.png", "游戏窗口实测帧-1036x831.png"),
    (r"D:\work\_downloads\live_q.png", "实况题面-图标与问题.png"),
    (r"D:\work\_downloads\live_o.png", "实况选项区-火眼金睛等四选项.png"),
    (r"D:\work\_downloads\live_box_check.png", "红框对位验证-套住火眼金睛.png"),
    (os.path.join(base, "xiangshi.png"), "乡试合成测试图.png"),
    (os.path.join(base, "yuanxiao.png"), "元宵合成测试图.png"),
    (os.path.join(base, "huishi_synth.png"), "会试合成测试图.png"),
]
for src, dst in pairs:
    if os.path.exists(src):
        shutil.copyfile(src, os.path.join(OUT, dst))
        print("archived:", dst)
    else:
        print("missing:", src)
