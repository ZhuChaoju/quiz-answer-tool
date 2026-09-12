# -*- coding: utf-8 -*-
import shutil

# 用户录入的实拍哈希在 release 侧，同步回仓库副本保持一致
shutil.copyfile(r"dist\release\banks\teachers\icons.json", r"banks\teachers\icons.json")
print("icons.json synced release -> repo")
