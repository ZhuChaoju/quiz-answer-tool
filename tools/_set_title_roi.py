# -*- coding: utf-8 -*-
import ast
import io
import json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# 给所有模块配置加 title ROI + title keywords
ROOT = r"D:\work\quiz-answer-tool"

# 科举（乡试/会试共用）：标题条 "乡试"/"会试"
keju = json.load(open(rf"{ROOT}\banks\keju\modules\keju.json", encoding="utf-8-sig"))
keju["roi"]["title"] = {"x": 42.0, "y": 24.0, "w": 16.0, "h": 4.5}
keju["title_keywords"] = ["乡试", "会试"]
json.dump(keju, open(rf"{ROOT}\banks\keju\modules\keju.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("keju ok")

# 教师节：标题条 "看图说话"
teachers = json.load(open(rf"{ROOT}\banks\teachers\module.json", encoding="utf-8-sig"))
teachers["roi"]["title"] = {"x": 42.0, "y": 24.0, "w": 16.0, "h": 4.5}
teachers["title_keywords"] = ["看图说话"]
json.dump(teachers, open(rf"{ROOT}\banks\teachers\module.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("teachers ok")

# 元宵：标题条 "元宵"/"灯谜"
yuanxiao = json.load(open(rf"{ROOT}\banks\yuanxiao\module.json", encoding="utf-8-sig"))
yuanxiao["roi"]["title"] = {"x": 42.0, "y": 24.0, "w": 16.0, "h": 4.5}
yuanxiao["title_keywords"] = ["元宵", "灯谜"]
json.dump(yuanxiao, open(rf"{ROOT}\banks\yuanxiao\module.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("yuanxiao ok")

# 同步到 release
for src, dst in [
    (rf"{ROOT}\banks\keju\modules\keju.json", rf"{ROOT}\dist\release\banks\keju\modules\keju.json"),
    (rf"{ROOT}\banks\teachers\module.json", rf"{ROOT}\dist\release\banks\teachers\module.json"),
    (rf"{ROOT}\banks\yuanxiao\module.json", rf"{ROOT}\dist\release\banks\yuanxiao\module.json"),
]:
    shutil.copyfile(src, dst)
print("release synced")
