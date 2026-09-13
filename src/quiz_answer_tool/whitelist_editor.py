# -*- coding: utf-8 -*-
"""白名单编辑器：查看/增删白名单 + 按答案查找并删除占用条目。

从工具主窗口的「白名单」按钮打开（作为子窗口）。白名单与题库/图标库的
修改通过「保存并关闭」写盘。
"""
import io
import json
import os
import sys
import tkinter as tk
from tkinter import ttk

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


class WhitelistEditor(tk.Toplevel):
    def __init__(self, mod, master=None):
        self.mod = mod
        super().__init__(master)
        self.title(f"白名单与答案管理 - {mod.name}")
        self.geometry("780x580")
        self._build()
        self._refresh_all()

    # ---- 构建 ----
    def _build(self):
        head = ttk.Frame(self, padding=6)
        head.pack(fill="x")
        ttk.Label(head, text=f"活动: {self.mod.name}").pack(side="left")
        ttk.Button(head, text="保存并关闭", command=self._save_close).pack(side="right")

        mid = ttk.Frame(self, padding=6)
        mid.pack(fill="both", expand=True)
        ttk.Label(mid, text="白名单（名单内的答案允许在多个条目上重复）").pack(anchor="w")
        row = ttk.Frame(mid)
        row.pack(fill="both", expand=True)
        self._wl_list = tk.Listbox(row, height=7)
        self._wl_list.pack(side="left", fill="both", expand=True)
        btns = ttk.Frame(row)
        btns.pack(side="left", padx=6)
        ttk.Button(btns, text="删除选中", command=self._wl_del).pack(anchor="w", pady=2)
        er = ttk.Frame(btns)
        er.pack(anchor="w", pady=4)
        self._wl_var = tk.StringVar()
        ttk.Entry(er, textvariable=self._wl_var, width=14).pack(side="left")
        ttk.Button(er, text="添加", command=self._wl_add).pack(side="left", padx=2)

        ttk.Separator(mid).pack(fill="x", pady=6)
        ttk.Label(mid, text="按答案查找占用条目（选中后可删除）").pack(anchor="w")
        row2 = ttk.Frame(mid)
        row2.pack(fill="x")
        self._q_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self._q_var, width=24).pack(side="left")
        ttk.Button(row2, text="查找", command=self._refresh_hits).pack(side="left", padx=4)
        self._hit_list = tk.Listbox(row2, height=6)
        self._hit_list.pack(fill="both", expand=True)
        ttk.Button(mid, text="删除选中的占用条目", command=self._del_hit).pack(anchor="w", pady=4)

    # ---- 刷新 ----
    def _refresh_all(self):
        self._refresh_wl()
        self._refresh_hits()

    def _refresh_wl(self):
        self._wl_list.delete(0, tk.END)
        for n in self.mod.answer_whitelist:
            self._wl_list.insert(tk.END, n)

    def _refresh_hits(self):
        ans = self._q_var.get().strip()
        self._hit_list.delete(0, tk.END)
        if not ans:
            return
        bank = self.mod.bank
        if bank is None:
            return
        if hasattr(bank, "names_with_answer"):
            for n in bank.names_with_answer(ans):
                self._hit_list.insert(tk.END, f"[图标] {n}")
        if hasattr(bank, "find_by_answer"):
            for e in bank.find_by_answer(ans):
                self._hit_list.insert(tk.END, f"[题目] {e.get('question', '')[:44]} → {e.get('answer', '')}")

    # ---- 操作 ----
    def _wl_add(self):
        t = self._wl_var.get().strip()
        if t and t not in self.mod.answer_whitelist:
            self.mod.answer_whitelist.append(t)
        self._wl_var.set("")
        self._refresh_wl()

    def _wl_del(self):
        sel = self._wl_list.curselection()
        if sel:
            self.mod.answer_whitelist.pop(sel[0])
        self._refresh_wl()

    def _del_hit(self):
        sel = self._hit_list.curselection()
        if not sel:
            return
        text = self._hit_list.get(sel[0])
        if text.startswith("[图标] "):
            self.mod.bank.remove_name(text[5:].strip())
        elif text.startswith("[题目] "):
            q = text[4:].split(" → ")[0].strip()
            self.mod.bank.remove(q)
        self._save_entries()
        self._refresh_hits()

    def _save_entries(self):
        """把内存中的题库/图标库写盘。"""
        import json

        mod = self.mod
        if mod.type == "icon":
            mod.bank.save(os.path.join(mod.bank_dir, "icons.json"))
        elif mod.bank is not None:
            bank_path = os.path.join(mod.bank_dir, "questions.json")
            with open(bank_path, "w", encoding="utf-8") as f:
                json.dump(mod.bank._raw, f, ensure_ascii=False, indent=1)

    def _save_close(self):
        self._save_entries()
        wl = os.path.join(self.mod.bank_dir, "whitelist.json")
        with open(wl, "w", encoding="utf-8") as f:
            json.dump(self.mod.answer_whitelist, f, ensure_ascii=False, indent=2)
        self.destroy()
