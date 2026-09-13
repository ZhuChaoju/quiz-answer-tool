# -*- coding: utf-8 -*-
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from PIL import Image

import os

d = r"C:\Users\zcj\Downloads\截图\科举"
for fn in sorted(os.listdir(d)):
    if fn.startswith("screenshot"):
        img = Image.open(os.path.join(d, fn))
        print(fn, img.size)
