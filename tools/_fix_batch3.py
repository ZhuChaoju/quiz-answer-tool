# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"tools\batch_verify.py"
s = open(p, encoding="utf-8").read()
old = """    # 游戏窗口在桌面左上角 (0,0)，物理尺寸 1295x1039 → 按截图比例裁剪
    sx, sy = W / 3840.0, H / 2160.0
    gw, gh = int(1295 * sx), int(1039 * sy)
    if gw < 400 or gh < 300:
        print(f"{fn}: 截图尺寸异常跳过")
        continue
    frame = img.crop((0, 0, gw, gh)).resize((FW, FH), Image.LANCZOS)"""
new = """    # 游戏窗口在桌面左上角 (0,0)：原生窗口截图(1295x1039)按 1:1 裁剪；
    # 桌面大截图同样从左上角裁出游戏窗口区域
    gw = min(W, 1295)
    gh = min(H, 1039)
    if gw < 400 or gh < 300:
        print(f"{fn}: 截图尺寸异常跳过")
        continue
    frame = img.crop((0, 0, gw, gh)).resize((FW, FH), Image.LANCZOS)"""
assert old in s, "crop pattern"
s = s.replace(old, new, 1)
ast.parse(s)
open(p, "w", encoding="utf-8").write(s)
print("batch crop fixed")
