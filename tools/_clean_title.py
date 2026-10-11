# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
for p in (r"banks\keju\modules\keju.json", r"banks\teachers\module.json", r"banks\yuanxiao\module.json"):
    s = open(p, encoding="utf-8").read()
    if "title_keywords" in s:
        # 用正则删
        import re

        s = re.sub(r'"title_keywords":\s*\[[^\]]*\],?\s*\n?', "", s)
        s = re.sub(r'"title":\s*\{[^}]*\},?\s*\n?', "", s)
        open(p, "w", encoding="utf-8").write(s)
        print("cleaned:", p)
for p in (r"dist\release\banks\keju\modules\keju.json",
          r"dist\release\banks\teachers\module.json",
          r"dist\release\banks\yuanxiao\module.json"):
    if os.path.exists(p):
        s = open(p, encoding="utf-8").read()
        if "title_keywords" in s:
            s = re.sub(r'"title_keywords":\s*\[[^\]]*\],?\s*\n?', "", s)
            s = re.sub(r'"title":\s*\{[^}]*\},?\s*\n?', "", s)
            open(p, "w", encoding="utf-8").write(s)
            print("cleaned:", p)
import os
print("done")
