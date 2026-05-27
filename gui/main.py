#!/usr/bin/env python3
import sys
import os

# 将 gui/ 目录加入 sys.path，使 core/ 和 tabs/ 可直接 import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import App

if __name__ == "__main__":
    app = App()
    app.mainloop()
