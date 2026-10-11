# -*- coding: utf-8 -*-
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from PIL import Image

d = r"C:\Users\zcj\Downloads\截图\科举\乡试"
for fn in sorted(os.listdir(d)):
    if fn.startswith("ScreenShot"):
        img = Image.open(os.path.join(d, fn))
        print(fn, img.size)
        img.convert("RGB").resize((img.width // 2, img.height // 2), Image.LANCZOS).save(
            rf"D:\work\_downloads\xs_{fn[:30]}.png"
        )
print("thumbs saved")
