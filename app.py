import os
import sys
import json
import re
import webbrowser
import urllib.request
from datetime import datetime

# 打包后资源在 sys._MEIPASS，开发时在脚本同目录
BASE_DIR = sys._MEIPASS if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))


def resource_path(name):
    return os.path.join(BASE_DIR, name)


# ---------------------------------------------------------------------------
# 真实数据后端（pywebview 通信桥）
# 行情/快讯经 Python 拉取 —— 绕过浏览器跨域(CORS)限制，拿到完整真实数据。
# 前端通过 window.pywebview.api.* 调用（见 index.html 的 loadBridgeEvents）。
# ---------------------------------------------------------------------------
NEWS_URL = "https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2509&num=40&page=1"
QT_URL = "https://qt.gtimg.cn/q="


class StockPulseAPI:
    """暴露给前端 JS 的方法集合（window.pywebview.api.*）"""

    def get_events(self):
        """拉取真实财经快讯（新浪滚动新闻）；前端复用 classify/mapAffected 做影响分析"""
        try:
            req = urllib.request.Request(NEWS_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            items = (data.get("result") or {}).get("data") or []
            out = []
            for it in items:
                title = (it.get("title") or "").strip()
                if not title:
                    continue
                media = it.get("media") or "新浪财经"
                ctime = it.get("ctime") or it.get("intime") or ""
                try:
                    t = datetime.fromtimestamp(int(ctime)).strftime("%H:%M")
                except Exception:
                    t = ""
                out.append({
                    "title": title,
                    "body": (it.get("intro") or "").strip(),
                    "src": media,
                    "time": t,
                    "market": "综合",
                    "cat": "财经快讯",
                    "real": True,
                })
            return out[:40]
        except Exception as e:
            return [{"error": str(e)}]

    def get_quote(self, code):
        """拉取单只 A股实时行情（腾讯接口）"""
        sym = ("sh" if code[:1] in ("6", "9") else "sz") + code
        try:
            req = urllib.request.Request(QT_URL + sym, headers={
                "User-Agent": "Mozilla/5.0", "Referer": "https://gu.qq.com/"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read().decode("gbk", "ignore")
            m = re.search(r'="([^"]*)"', raw)
            if not m:
                return {"error": "no data"}
            f = m.group(1).split("~")
            price = float(f[3]); prev = float(f[4])
            return {"code": code, "name": f[1], "price": price, "prev": prev,
                    "pct": round((price - prev) / prev * 100, 2)}
        except Exception as e:
            return {"error": str(e)}


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
        api = StockPulseAPI()
        webview.create_window(
            "智讯股研 · StockPulse AI",
            url,
            js_api=api,
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
