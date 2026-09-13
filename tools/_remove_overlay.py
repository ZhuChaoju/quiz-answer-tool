# -*- coding: utf-8 -*-
"""删除答题浮窗功能 + 启动窗口加大。所有替换带断言，防静默失败。"""
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"src\quiz_answer_tool\viewer.py"
s = open(p, encoding="utf-8").read()


def rep(old, new, tag):
    global s
    assert old in s, f"NOT FOUND: {tag}"
    s = s.replace(old, new, 1)
    print("ok:", tag)


# 1) import
rep("from .overlay import AnswerOverlay\n", "", "overlay import")

# 2) __init__ 变量
rep("""        self._overlay_on = tk.BooleanVar(value=bool(ui.get("overlay", True)))
        self._clickthrough = tk.BooleanVar(value=False)
""", "", "init vars")

# 3) _build_ui 第二行浮窗勾选
rep("""        ttk.Checkbutton(second, text="答题浮窗", variable=self._overlay_on, command=self._sync_overlay).pack(
            side="left", padx=(14, 0)
        )
        ttk.Checkbutton(second, text="浮窗鼠标穿透", variable=self._clickthrough, command=self._sync_overlay).pack(
            side="left", padx=(14, 0)
        )
""", "", "overlay checkboxes")

# 4) _on_module_changed 浮窗换位
rep("""        self._sync_overlay()
        if self._overlay and self._overlay.win.winfo_exists():
            pos = self.cfg.get("ui", {}).get("overlay_pos", {}).get(self._module.id)
            if pos:
                self._overlay.move_to(int(pos[0]), int(pos[1]))
        self._update_roi_label()""",
    """        self._update_roi_label()""",
    "module changed overlay block")

# 5) _sync_overlay + _remember_overlay_pos 整段删除
i = s.find("    # ---------- 浮窗 ----------")
j = s.find("    # ---------- 来源 ----------")
assert 0 < i < j, "overlay section markers"
s = s[:i] + s[j:]
print("ok: _sync_overlay section removed")

# 6) _save_config 浮窗位置
rep("""        overlay_pos = dict(ui.get("overlay_pos", {}))
        for mid, pos in getattr(self, "_overlay_pos_by_mod", {}).items():
            overlay_pos[mid] = list(pos)
        if self._overlay and self._overlay.win.winfo_exists():
            overlay_pos[self._module.id] = [self._overlay.win.winfo_x(), self._overlay.win.winfo_y()]
        ui["overlay_pos"] = overlay_pos
""", "", "save overlay_pos")

# 7) _poll_queues 浮窗更新
rep("""                    if self._overlay and self._overlay.win.winfo_exists():
                        ans = result.answer
                        if result.state == "soft_hit":
                            ans = f"{ans}？" if ans else "未命中"
                        self._overlay.update(result.question, ans, result.note)
""", """                    if result.state == "soft_hit":
                        self._set_text(self._a_text, f"答案(待核对): {result.answer}")
""", "poll soft display")

# 8) _on_close 浮窗关闭
rep("""        if self._overlay and self._overlay.win.winfo_exists():
            self._overlay.close()
""", "", "close overlay")

# 9) 启动窗口加大
rep('self.geometry("1400x950")', 'self.geometry("2000x1350")', "geometry")

open(p, "w", encoding="utf-8").write(s)
ast.parse(s)
print("ALL DONE, syntax ok")
