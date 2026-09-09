# -*- coding: utf-8 -*-
"""活动模块包：每个活动一个模块（科举乡试/会试、教师节、元宵节……），各自绑定题库/素材库。"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from .base import BaseModule, ModuleResult, Roi
from .icon import IconModule
from .text import TextModule

_MODULE_TYPES: dict[str, type[BaseModule]] = {
    "text": TextModule,
    "icon": IconModule,
}


def _load_module_json(path: str) -> dict[str, Any]:
    # utf-8-sig：兼容记事本保存的带 BOM 配置
    with open(path, encoding="utf-8-sig") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"模块配置必须是 JSON 对象: {path}")
    return data


def load_modules(banks_dir: str) -> list[BaseModule]:
    """扫描 banks 目录装配全部活动模块。

    目录约定（题库分模块成文件夹）：
      banks/<库>/module.json          单模块库（如 teachers/、yuanxiao/）
      banks/<库>/modules/*.json       多模块共享同一题库（如 keju/ 下乡试+会试）
    模块内 bank 路径相对 banks/<库>/。
    """
    modules: list[BaseModule] = []
    if not os.path.isdir(banks_dir):
        return modules
    for bank_name in sorted(os.listdir(banks_dir)):
        bank_dir = os.path.join(banks_dir, bank_name)
        if not os.path.isdir(bank_dir):
            continue
        candidates: list[str] = []
        modules_dir = os.path.join(bank_dir, "modules")
        if os.path.isdir(modules_dir):
            candidates.extend(
                os.path.join(modules_dir, fn)
                for fn in sorted(os.listdir(modules_dir))
                if fn.endswith(".json")
            )
        elif os.path.exists(os.path.join(bank_dir, "module.json")):
            candidates.append(os.path.join(bank_dir, "module.json"))
        for path in candidates:
            try:
                data = _load_module_json(path)
                mtype = data.get("type", "text")
                cls = _MODULE_TYPES.get(mtype)
                if cls is None:
                    raise ValueError(f"未知模块类型: {mtype}")
                modules.append(cls.from_json(data, bank_dir))
            except Exception as exc:  # 单个模块配置坏了不拖垮整体
                print(f"[banks] 加载模块失败 {path}: {exc}")
    return modules


__all__ = [
    "BaseModule",
    "ModuleResult",
    "Roi",
    "TextModule",
    "IconModule",
    "load_modules",
    "field",
    "dataclass",
]
