# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"src\quiz_answer_tool\viewer.py"
s = open(p, encoding="utf-8").read()

old = """                if cur == last_hash:
                    continue
                last_hash = cur
                # 画面已变化：立即清掉上一题的红框/动态选项框，避免新题出来时残留
                self._result_queue.put(("clear",))"""
new = """                if cur == last_hash:
                    continue
                # 识别频率上限：动画画面会让闸门频繁变化，全量 OCR 最高 3 次/秒，
                # 防止 CPU 被连续识别打满（0.33s 内的中间变化直接跳过）
                now_t = time.perf_counter()
                if now_t - last_rec_t < 0.33:
                    continue
                last_rec_t = now_t
                last_hash = cur
                # 画面已变化：立即清掉上一题的红框/动态选项框，避免新题出来时残留
                self._result_queue.put(("clear",))"""
assert old in s, "pattern not found"
s = s.replace(old, new, 1)

old2 = """            last_hash: tuple | None = None
            last_mod_id: str | None = None"""
new2 = """            last_hash: tuple | None = None
            last_rec_t = 0.0
            last_mod_id: str | None = None"""
assert old2 in s, "init pattern not found"
s = s.replace(old2, new2, 1)

open(p, "w", encoding="utf-8").write(s)
ast.parse(s)
print("rate limit added, syntax ok")
