# -*- coding: utf-8 -*-
"""文字模块端到端测试：科举·会试(真实网图) + 科举·乡试/元宵节(合成题图)。

合成图按各模块 ROI 预设的几何摆放题面与选项，模拟游戏对话框布局；
验证 OCR→清理→题库匹配→答案→红框定位全链路。
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from quiz_answer_tool.activities import load_modules  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OCR_CFG = {"model_type": "tiny", "lang": "ch", "confidence": 0.4, "use_dml": False}


def find_font(size: int) -> str:
    for p in (
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
    ):
        if os.path.exists(p):
            return p
    raise RuntimeError("no CJK font")


def render_dialog(path: str, size: tuple[int, int], dialog: tuple[int, int, int, int],
                  q_rect: tuple[int, int, int, int], o_rect: tuple[int, int, int, int],
                  question: str, options: list[str], vertical: bool = False) -> None:
    """在 size 画面中画对话框；题面画进 q_rect、选项画进 o_rect（与模块 ROI 对齐）。"""
    img = Image.new("RGB", size, (40, 60, 50))
    d = ImageDraw.Draw(img)
    d.rectangle(dialog, fill=(168, 164, 210))
    font = ImageFont.truetype(find_font(22), 22)
    ql, qt, qr, qb = q_rect
    # 手动折行（矩形内每行约 (qr-ql-40)/22 个字）
    max_chars = max(8, int((qr - ql - 40) / 24))
    lines = [question[i:i + max_chars] for i in range(0, len(question), max_chars)]
    y = qt + 12
    for ln in lines:
        d.text((ql + 20, y), ln, fill=(30, 30, 80), font=font)
        y += 30
    ol, ot, or_, ob = o_rect
    if vertical:
        oy = ot + 8
        for name in options:
            d.text((ol + 40, oy), name, fill=(60, 40, 10), font=font)
            oy += 36
    else:
        col_w = (or_ - ol - 40) / 2
        row_h = (ob - ot - 20) / 2
        for i, name in enumerate(options):
            cx = ol + 20 + (i % 2) * col_w
            cy = ot + 10 + (i // 2) * row_h
            d.rectangle((cx, cy, cx + col_w - 20, cy + min(48, row_h - 8)), fill=(196, 193, 226))
            d.text((cx + 40, cy + 12), name, fill=(20, 20, 20), font=font)
    img.save(path)


def main() -> None:
    mods = {m.id: m for m in load_modules(os.path.join(ROOT, "banks"))}
    assert set(mods) == {"teachers", "keju_huishi", "keju_xiangshi", "yuanxiao"}, mods.keys()
    tmp = os.path.join(ROOT, "build", "test_frames")
    os.makedirs(tmp, exist_ok=True)
    passed = failed = 0

    # ---- 1) 科举·会试：真实网图 ----
    huishi_img = r"D:\work\_downloads\keju_huishi_web.jpg"
    mod = mods["keju_huishi"]
    r = mod.recognize(Image.open(huishi_img).convert("RGB"), OCR_CFG)
    print(f"[keju_huishi 网图] ans={r.answer!r} line={r.answer_line is not None} q={r.question[:30]}...")
    if r.answer == "水":
        passed += 1
    else:
        failed += 1
        print("   FAIL: expect 水")

    # ---- 2) 科举·乡试：合成竖排题图（题面取自真题库） ----
    import json

    def roi_rect(mod, key, size):
        l, t, r, b = mod.rois[key].rect_px(size)
        return int(l) + 6, int(t) + 6, int(r) - 6, int(b) - 6

    bank = json.load(open(os.path.join(ROOT, "banks", "keju", "questions.json"), encoding="utf-8-sig"))
    q1 = next(q for q in bank if q["question"].startswith("梦幻西游中有多少个种族"))
    size = (1024, 768)
    mx = mods["keju_xiangshi"]
    p1 = os.path.join(tmp, "xiangshi.png")
    render_dialog(p1, size, (230, 100, 850, 660),
                  roi_rect(mx, "question", size), roi_rect(mx, "option", size),
                  f"第3题：{q1['question']}", ["3", "6", "9"], vertical=True)
    t0 = time.perf_counter()
    r = mx.recognize(Image.open(p1).convert("RGB"), OCR_CFG)
    dt = (time.perf_counter() - t0) * 1000
    print(f"[keju_xiangshi 合成] ans={r.answer!r} expect={q1['answer']!r} {dt:.0f}ms line={r.answer_line is not None} note={r.note}")
    if r.answer == q1["answer"]:
        passed += 1
    else:
        failed += 1

    # ---- 3) 元宵节：合成网格题图（灯谜真题） ----
    ybank = json.load(open(os.path.join(ROOT, "banks", "yuanxiao", "questions.json"), encoding="utf-8-sig"))
    q2 = next(q for q in ybank if q["question"].startswith('歇后语"泥菩萨过河"'))
    p2 = os.path.join(tmp, "yuanxiao.png")
    my = mods["yuanxiao"]
    render_dialog(p2, size, (230, 100, 850, 660),
                  roi_rect(my, "question", size), roi_rect(my, "option", size),
                  f"灯谜：{q2['question']}", ["有去无回", "自身难保", "越洗越脏", "一步登天"])
    t0 = time.perf_counter()
    r = my.recognize(Image.open(p2).convert("RGB"), OCR_CFG)
    dt = (time.perf_counter() - t0) * 1000
    print(f"[yuanxiao 合成] ans={r.answer!r} expect={q2['answer']!r} {dt:.0f}ms line={r.answer_line is not None} note={r.note}")
    if r.answer == q2["answer"]:
        passed += 1
    else:
        failed += 1

    # ---- 4) 会试：合成题图（含关卡前缀+自动折行） ----
    q3 = next(q for q in bank if "中医将五脏与五行相对应" in q["question"])
    p3 = os.path.join(tmp, "huishi_synth.png")
    mh = mods["keju_huishi"]
    render_dialog(p3, size, (330, 90, 990, 680),
                  roi_rect(mh, "question", size), roi_rect(mh, "option", size),
                  f"御前科举大赛第1关：这一关考的是茶酒中药。题目：{q3['question']}",
                  ["金", "水", "木", "火"])
    r = mh.recognize(Image.open(p3).convert("RGB"), OCR_CFG)
    print(f"[keju_huishi 合成] ans={r.answer!r} expect={q3['answer']!r} line={r.answer_line is not None} note={r.note}")
    if r.answer == q3["answer"]:
        passed += 1
    else:
        failed += 1

    print(f"\ntext modules: {passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
