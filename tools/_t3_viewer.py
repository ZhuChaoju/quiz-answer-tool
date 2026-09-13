# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ---- viewer.py: 白名单按钮 + 录入查重 ----
p = r"src\quiz_answer_tool\viewer.py"
s = open(p, encoding="utf-8").read()

# 1) 工具栏加白名单按钮（放在保存为预设右侧）
old = """        ttk.Button(top, text="保存为预设", command=self._save_preset).pack(side="right", padx=6)"""
new = """        ttk.Button(top, text="保存为预设", command=self._save_preset).pack(side="right", padx=6)
        ttk.Button(top, text="白名单", command=self._open_whitelist).pack(side="right", padx=6)"""
assert old in s, "toolbar pattern"
s = s.replace(old, new, 1)

# 2) 打开编辑器方法
old2 = """    # ---------- 来源 ----------
    def _reload_sources(self) -> None:"""
new2 = """    def _open_whitelist(self) -> None:
        from .whitelist_editor import WhitelistEditor

        WhitelistEditor(self._module, master=self)

    # ---------- 来源 ----------
    def _reload_sources(self) -> None:"""
assert old2 in s, "reload pattern"
s = s.replace(old2, new2, 1)

# 3) 录入查重（图标模块：技能名占用；文字模块：答案占用）
old3 = """        mod = self._module
        if mod.type == "icon":
            if mod.last_hash is None:
                self._set_text(self._a_text, "没有可收录的图标（先识别一次）")
                return
            mod.bank.add(mod.last_hash, text)
            if mod.config_path():
                try:
                    mod.bank.save(os.path.join(mod.bank_dir, "icons.json"))
                except OSError as exc:
                    self._set_text(self._a_text, f"写入图标库失败: {exc}")
                    return
            self._set_text(self._a_text, f"已收录图标: {text}（共 {len(mod.bank)} 个）")
        else:
            q = getattr(mod, "last_question", "")
            if not q:
                self._set_text(self._a_text, "没有可收录的题目（先识别一次未命中题目）")
                return
            mod.bank.add(q, text)
            bank_path = os.path.join(mod.bank_dir, "questions.json")
            try:
                with open(bank_path, encoding="utf-8-sig") as f:
                    data = json.load(f)
                hit = next((it for it in data if it.get("question") == q), None)
                if hit is None:
                    data.append({"id": len(data) + 1, "question": q, "options": [], "answer": text})
                else:
                    hit["answer"] = text
                with open(bank_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=1)
            except OSError as exc:
                self._set_text(self._a_text, f"写入题库失败: {exc}")
                return
            self._set_text(self._a_text, f"已收录: {q} → {text}")
        self._entry_var.set("")"""
new3 = """        mod = self._module
        # 答案全局唯一（按活动分开）：同名答案已占用时拒绝录入，白名单豁免
        owners = []
        if mod.type == "icon" and mod.bank is not None:
            owners = mod.bank.names_with_answer(text)
        elif mod.type == "text" and mod.bank is not None:
            owners = [e.get("question", "")[:36] for e in mod.bank.find_by_answer(text)]
        whitelisted = text in getattr(mod, "answer_whitelist", [])
        if owners and not whitelisted:
            self._set_text(
                self._a_text,
                f"无法录入：「{text}」已存在于 {len(owners)} 个条目（{'、'.join(owners[:3])}"
                f"{'…' if len(owners) > 3 else ''}）。加入白名单可允许多条，或先删除占用条目",
            )
            return
        if mod.type == "icon":
            if mod.last_hash is None:
                self._set_text(self._a_text, "没有可收录的图标（先识别一次）")
                return
            mod.bank.add(mod.last_hash, text)
            if mod.config_path():
                try:
                    mod.bank.save(os.path.join(mod.bank_dir, "icons.json"))
                except OSError as exc:
                    self._set_text(self._a_text, f"写入图标库失败: {exc}")
                    return
            extra = "（白名单，允许多条）" if whitelisted else ""
            self._set_text(self._a_text, f"已收录图标: {text}（共 {len(mod.bank)} 个）{extra}")
        else:
            q = getattr(mod, "last_question", "")
            if not q:
                self._set_text(self._a_text, "没有可收录的题目（先识别一次未命中题目）")
                return
            mod.bank.add(q, text)
            bank_path = os.path.join(mod.bank_dir, "questions.json")
            try:
                with open(bank_path, encoding="utf-8-sig") as f:
                    data = json.load(f)
                hit = next((it for it in data if it.get("question") == q), None)
                if hit is None:
                    data.append({"id": len(data) + 1, "question": q, "options": [], "answer": text})
                else:
                    hit["answer"] = text
                with open(bank_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=1)
            except OSError as exc:
                self._set_text(self._a_text, f"写入题库失败: {exc}")
                return
            self._set_text(self._a_text, f"已收录: {q} → {text}")
        self._entry_var.set("")"""
assert old3 in s, "add answer pattern"
s = s.replace(old3, new3, 1)
ast.parse(s)
open(p, "w", encoding="utf-8").write(s)
print("viewer whitelist + uniqueness ok")
