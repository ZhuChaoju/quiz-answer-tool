# -*- coding: utf-8 -*-
"""启动工具：源码/配置比 exe 新时自动重打包，保证启动的是最新版本。

规则（用户明确要求）：每次启动都必须是最新版本。
同时保护 release 里的 config.json（用户偏好）与 banks 数据不被仓库副本覆盖。
"""
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
EXE = os.path.join(ROOT, "dist", "release", "quiz-answer-tool.exe")


def newest_mtime(path: float | None, folder: str, exts: tuple) -> float:
    best = path or 0.0
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "bin", "obj")]
        for f in files:
            if f.endswith(exts):
                mt = os.path.getmtime(os.path.join(root, f))
                best = max(best, mt)
    return best


def main() -> None:
    exe_mt = os.path.getmtime(EXE) if os.path.exists(EXE) else 0
    src_newest = newest_mtime(exe_mt, os.path.join(ROOT, "src"), (".py",))
    banks_newest = newest_mtime(exe_mt, os.path.join(ROOT, "banks"), (".json", ".png"))
    cfg_newest = os.path.getmtime(os.path.join(ROOT, "config", "config.example.json"))

    need_build = max(src_newest, banks_newest, cfg_newest) > exe_mt
    if need_build:
        print("[启动] 检测到源码/配置更新，重新打包（约 60~90 秒）...")
        r = subprocess.run(
            [os.path.join(ROOT, "build_exe.bat")],
            cwd=ROOT, shell=True,
            capture_output=True, text=True,
        )
        if "[OK]" not in r.stdout:
            print(r.stdout[-1500:])
            sys.exit("[启动] 打包失败")
        print("[启动] 打包完成")
    else:
        print("[启动] exe 已是最新版本")

    # 杀掉运行中的旧实例（保证这次启动用的是新 exe）
    subprocess.run(["taskkill", "/f", "/im", "quiz-answer-tool.exe"],
                   capture_output=True, text=True)
    time.sleep(2)

    print("[启动] 启动工具...")
    subprocess.Popen([EXE], cwd=os.path.dirname(EXE))
    print("[启动] 完成")


if __name__ == "__main__":
    main()
