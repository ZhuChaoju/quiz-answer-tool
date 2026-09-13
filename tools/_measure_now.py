# -*- coding: utf-8 -*-
import io
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import subprocess

r = subprocess.run(
    ["powershell", "-NoProfile", "-Command",
     "$p = Get-Process quiz-answer-tool -ErrorAction SilentlyContinue | Sort-Object CPU -Descending;"
     "$p | ForEach-Object { Write-Output ('{0} pid={1} cpu={2}' -f $_.Name, $_.Id, [math]::Round($_.CPU, 1)) };"
     "if ($p) { $main = $p[0]; $c0 = $main.CPU; Start-Sleep -Seconds 5; $main.Refresh(); $c1 = $main.CPU;"
     "Write-Output ('main_pid_delta_cores=' + [math]::Round(($c1 - $c0) / 5, 2)) }"],
    capture_output=True, text=True,
)
print(r.stdout)
print(r.stderr[:200] if r.stderr else "")
