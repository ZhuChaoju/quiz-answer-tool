# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"src\quiz_answer_tool\viewer.py"
s = open(p, encoding="utf-8").read()

old = """            last_hash: tuple | None = None
            last_mod_id: str | None = None
            while alive():
                time.sleep(interval)
                mod = self._module  # 运行中切活动，下一轮立即生效
                gate_key = "question" if "question" in mod.rois else "icon"
                if mod.id != last_mod_id:
                    last_mod_id = mod.id
                    last_hash = None
                try:
                    frame, _ = screen.capture(source)
                    # 变化闸门覆盖题面/图标 + 选项两个区域：
                    # 同图标但选项换位时也要重新识别，否则红框残留指错位置
                    gate_main = _dhash(mod.rois[gate_key].crop(frame, pad=0.02))
                    gate_opt = _dhash(mod.rois["option"].crop(frame, pad=0.02))
                    cur = (gate_main, gate_opt)
                except Exception as exc:
                    self._result_queue.put(("error", f"截图失败: {exc}"))
                    continue
                if cur == last_hash:
                    continue
                last_hash = cur
                # 画面已变化：立即清掉上一题的红框/动态选项框，避免新题出来时残留
                self._result_queue.put(("clear",))
                try:
                    result = mod.recognize(frame, ocr_cfg)
                except Exception as exc:
                    self._result_queue.put(("error", f"识别失败: {exc}"))
                    continue
                self._result_queue.put(("result", result))"""

new = """            last_main: tuple | None = None
            last_opt: int | None = None
            pending_opt: int | None = None
            pending_count = 0
            last_mod_id: str | None = None
            while alive():
                time.sleep(interval)
                mod = self._module  # 运行中切活动，下一轮立即生效
                gate_key = "question" if "question" in mod.rois else "icon"
                if mod.id != last_mod_id:
                    last_mod_id = mod.id
                    last_main = last_opt = pending_opt = None
                try:
                    frame, _ = screen.capture(source)
                    # 两级变化闸门：题面/图标区 = 题目身份；选项区 = 选项布局。
                    # 选项区单独变化（同题换选项）只重新定位红框，不清答案不闪烁；
                    # 选项区去抖：连续两轮哈希一致才认定真的变了（过滤动画噪声）。
                    gate_main = _dhash(mod.rois[gate_key].crop(frame, pad=0.02))
                    gate_opt = _dhash(mod.rois["option"].crop(frame, pad=0.02))
                except Exception as exc:
                    self._result_queue.put(("error", f"截图失败: {exc}"))
                    continue

                def run_recognition():
                    try:
                        result = mod.recognize(frame, ocr_cfg)
                    except Exception as exc:
                        self._result_queue.put(("error", f"识别失败: {exc}"))
                        return
                    self._result_queue.put(("result", result))

                if gate_main != last_main:
                    # 新题目：清旧框 + 全量识别
                    last_main = gate_main
                    last_opt = gate_opt
                    pending_opt = None
                    self._result_queue.put(("clear",))
                    run_recognition()
                    continue
                if gate_opt != last_opt:
                    # 仅选项区变化：去抖两轮后重新定位红框（保留现有答案展示）
                    if gate_opt == pending_opt:
                        pending_count += 1
                    else:
                        pending_opt = gate_opt
                        pending_count = 1
                    if pending_count >= 2:
                        last_opt = gate_opt
                        pending_opt = None
                        run_recognition()
                    continue
                pending_opt = None"""

assert old in s, "ocr_loop pattern not found"
s = s.replace(old, new)
ast.parse(s)
open(p, "w", encoding="utf-8").write(s)
print("ocr_loop two-level gate applied, syntax ok")
