# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"tools\show_rois.py"
s = open(p, encoding="utf-8").read()
s = s.replace(
    'd_json = json.load(open(r"D:\\work\\quiz-answer-tool\\dist\\release\\banks\\keju\\modules\\keju_huishi.json", encoding="utf-8-sig"))',
    'import json as _j\n'
    'd_json = _j.load(open(r"D:\\work\\quiz-answer-tool\\banks\\keju\\modules\\keju.json", encoding="utf-8-sig"))',
)
s = s.replace('import json\n', '')
s = 'import json\nimport io\nimport os\nimport sys\n' + s[s.find('sys.stdout'):]
open(p, "w", encoding="utf-8").write(s)
import ast

ast.parse(s)
print("show_rois fixed")
