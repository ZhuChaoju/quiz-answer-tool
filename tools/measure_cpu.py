# -*- coding: utf-8 -*-
"""interval=0.05 下 CPU 占用测量：按 PID 精确采样运行中的测试进程。"""
import os
import subprocess
import sys
import time

proc = subprocess.Popen(
    [sys.executable, "-X", "utf8", os.path.join("tools", "test_live_loop.py")],
    cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    stdout=subprocess.PIPE,
)

# 测试在 t=0.3s 启动线程，t≈6.3s 停止 → 在 2~5.5s 之间采样 3.5 秒
time.sleep(2.0)

ps_script = f"""
$p = Get-Process -Id {proc.pid} -ErrorAction Stop
$c0 = $p.CPU
Start-Sleep -Milliseconds 3500
$p.Refresh()
$c1 = $p.CPU
Write-Output ('cpu_cores_used=' + [math]::Round(($c1 - $c0) / 3.5, 3))
"""
r = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True)
print(r.stdout.strip() or r.stderr.strip())
proc.wait()
out = proc.stdout.read().decode("utf-8", "replace")
print(out[-200:])
