#!/usr/bin/env python3
"""UCloud Cleaner Web 启动器（带 macOS 菜单栏托盘）
打包为 .app 后双击自动启动 Flask 服务并打开系统浏览器。
"""
import os
import subprocess
import sys
import threading
import time

# 自动安装缺失依赖
REQUIRED = ["flask", "pystray", "pillow"]

def _ensure_deps():
    for pkg in REQUIRED:
        try:
            __import__(pkg.replace("pillow", "PIL").replace("pystray", "pystray"))
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

_ensure_deps()

import pystray
from PIL import Image, ImageDraw
from web.app import create_app, _load_config


# ---------- 图标生成 ----------
def _create_icon():
    """生成一个简单的托盘图标（扫帚）"""
    width, height = 64, 64
    image = Image.new("RGBA", (width, height), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # 扫帚柄（棕色）
    draw.rectangle([30, 8, 36, 38], fill="#8B5A2B")
    # 扫帚头（黄色稻草）
    draw.polygon([(20, 38), (46, 38), (52, 58), (14, 58)], fill="#DAA520")
    # 扫帚头纹理线条
    draw.line([(24, 42), (20, 54)], fill="#B8860B", width=2)
    draw.line([(30, 42), (28, 54)], fill="#B8860B", width=2)
    draw.line([(36, 42), (36, 54)], fill="#B8860B", width=2)
    draw.line([(42, 42), (44, 54)], fill="#B8860B", width=2)

    return image


# ---------- 服务管理 ----------
class UCloudCleanerApp:
    def __init__(self):
        self.port = None
        self.url = None
        self.tray = None
        self._stop_event = threading.Event()

    def start(self):
        app, _ = create_app(testing=False)
        cfg = _load_config()
        self.port = int(cfg.get("port", 8080))
        self.url = f"http://127.0.0.1:{self.port}"

        # 启动 Flask
        def _serve():
            app.run(host="127.0.0.1", port=self.port, threaded=True, use_reloader=False)

        threading.Thread(target=_serve, daemon=True).start()

        # 等待服务就绪
        for _ in range(100):
            import socket
            try:
                s = socket.create_connection(("127.0.0.1", self.port), timeout=0.05)
                s.close()
                break
            except Exception:
                time.sleep(0.05)

        # 打开浏览器
        self._open_browser()

        # 创建托盘
        self.tray = pystray.Icon(
            "UCloudCleanerWeb",
            _create_icon(),
            "UCloud Cleaner Web",
            menu=pystray.Menu(
                pystray.MenuItem("打开浏览器", self._on_open_browser),
                pystray.MenuItem("停止服务并退出", self._on_exit),
            ),
        )
        self.tray.run()

    def _open_browser(self):
        if sys.platform == "darwin":
            subprocess.run(["open", self.url])
        elif sys.platform.startswith("win"):
            os.startfile(self.url)  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", self.url])

    def _on_open_browser(self):
        self._open_browser()

    def _on_exit(self):
        self.tray.stop()
        sys.exit(0)


def main():
    UCloudCleanerApp().start()


if __name__ == "__main__":
    main()
