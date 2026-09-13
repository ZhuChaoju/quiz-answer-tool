# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"src\quiz_answer_tool\viewer.py"
s = open(p, encoding="utf-8").read()

old = """                    gate_main = _dhash(mod.rois[gate_key].crop(frame, pad=0.02))
                    gate_opt = _dhash(mod.rois["option"].crop(frame, pad=0.02))"""
new = """                    gate_main = _dhash(mod.rois[gate_key].crop(frame, pad=0.02))
                    gate_opt = _dhash(mod.rois["option"].crop(frame, pad=0.02))
                    # 布局变体的题面区也纳入闸门（有图/无图布局切换会触发重识别）
                    gate_var = 0
                    for rv in getattr(mod, "roi_variants", []):
                        if "question" in rv:
                            gate_var ^= _dhash(rv["question"].crop(frame, pad=0.02))
                    cur = (gate_main, gate_opt, gate_var)"""
assert old in s, "gate pattern"
s = s.replace(old, new, 1)

old2 = """                if cur == last_hash:
                    continue
                last_hash = cur"""
new2 = """                if cur == last_hash:
                    continue
                # 识别频率上限：动画画面会频繁触发闸门，全量 OCR 最高 3 次/秒
                now_t = time.perf_counter()
                if now_t - last_rec_t < 0.33:
                    last_hash = cur
                    continue
                last_rec_t = now_t
                last_hash = cur"""
assert old2 in s, "rate pattern"
s = s.replace(old2, new2, 1)

old3 = """            last_main: tuple | None = None
            last_opt: int | None = None
            pending_opt: int | None = None
            pending_count = 0
            last_mod_id: str | None = None"""
new3 = """            last_main: tuple | None = None
            last_opt: int | None = None
            pending_opt: int | None = None
            pending_count = 0
            last_rec_t = 0.0
            last_mod_id: str | None = None"""
assert old3 in s, "init pattern"
s = s.replace(old3, new3, 1)

ast.parse(s)
open(p, "w", encoding="utf-8").write(s)
print("viewer gate variants + rate limit ok")
