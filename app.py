import os
import sys
import webbrowser

# 打包后资源在 sys._MEIPASS，开发时在脚本同目录
BASE_DIR = sys._MEIPASS if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))


def resource_path(name):
    return os.path.join(BASE_DIR, name)


def main():
    html = resource_path("index.html")
    if not os.path.exists(html):
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, "未找到 index.html，程序无法启动。", "StockPulse 错误", 0x10)
        except Exception:
            pass
        sys.exit(1)

    # 用 file:// 直接加载本地页面（原型为单文件自包含，无外部依赖）
    url = "file:///" + html.replace("\\", "/")
    try:
        import webview
        webview.create_window(
            "智讯股研 · StockPulse AI",
            url,
            width=1340,
            height=850,
            resizable=True,
            min_size=(900, 600),
        )
        webview.start()
    except Exception as e:
        # 回退：系统缺少 WebView2 时用默认浏览器打开，保证一定能用
        try:
            webbrowser.open(html)
        except Exception:
            pass
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0,
                "当前系统缺少 WebView2 运行环境，已改用默认浏览器打开。\n（错误：%s）" % e,
                "StockPulse",
                0x40,
            )
        except Exception:
            pass


if __name__ == "__main__":
    main()
