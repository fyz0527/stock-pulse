# 智讯股研 · StockPulse AI

跨市场资讯聚合与影响分析桌面应用（原型 / 演示版）。

> 把散落在 A 股、港股、美股及宏观/行业的新闻事件，自动映射到受影响的个股，并按你的「优先推送股票池」（含持仓）做智能置顶与实时提醒。

## ✨ 功能特性

- **跨市场资讯聚合**：A 股、港股、美股及宏观/行业资讯统一聚合、按时间流展示。
- **智能影响分析**：内置「受影响标的映射算法」，把事件标题/正文中的关键词映射到相关股票（A股/港股/美股）。
- **优先推送股票池**：
  - 自定义「关注」股票 + 「我的持仓」自动并入同一股票池；
  - 持仓标的显示绿色「持仓」徽章，关注显示橙色「关注」徽章；
  - 命中优先池的事件带 `P0` 徽章并**置顶**展示，「⚡即时推送」打破聚合延迟标记。
- **优先推送提醒**：顶部铃铛筛选优先事件；Toast 模拟实时推送（每 9 秒随机挑一优先股弹出提醒）。
- **私人投顾（二级页面）**：点击进入独立页面，针对你的持仓给出启发式解读。
- **水墨 + 现代金融风界面**：暖纸白底、印章 Logo、红紫品牌渐变。

## 📁 目录结构

```
.
├── index.html              # 主程序界面与全部逻辑（单文件自包含，无外部依赖）
├── app.py                  # pywebview 桌面入口，加载 index.html
├── StockPulse.spec         # PyInstaller 打包配置
├── build_pool.sh           # 一键打包为 exe（Windows 下用 Git Bash 运行）
├── test_syntax.js          # 打包前校验 index.html 内嵌 JS 语法
├── test_search.js          # 搜索/映射逻辑测试
├── PRD-智讯股研-*.md        # 产品需求文档
├── 深化-*.md               # 算法与方案深化设计文档
└── .gitignore
```

## 🔧 环境要求

- Python 3.10+
- 运行依赖：`pywebview`
- 打包依赖：`PyInstaller`
- Windows 需 WebView2 运行环境（Win11 自带；缺失时程序自动用默认浏览器打开并提示）

## 🚀 开发运行

```bash
pip install pywebview
python app.py
```

## 📦 打包为 exe（Windows）

在 **Git Bash** 中运行打包脚本（请勿与 node 语法校验用 `&&` 串联）：

```bash
bash build_pool.sh
```

- 脚本会先以 PyInstaller 生成 `dist/StockPulse.exe`（单文件、`--windowed`）；
- 打包前建议单独执行 `node test_syntax.js` 校验 `index.html` 内嵌 JS 语法；
- 产物 `dist/StockPulse.exe` 可直接复制到桌面双击运行。

## 🧱 技术栈

| 层 | 选型 |
| --- | --- |
| 前端 | 单文件 `index.html`（原生 HTML / CSS / JS，水墨风） |
| 桌面壳 | `pywebview`（基于系统 WebView2） |
| 打包 | `PyInstaller`（`--onefile --windowed --collect-all webview`） |
| 状态持久化 | 浏览器 `localStorage`（关注池 / 持仓） |

## 📝 数据说明

本仓库为**演示版**：行情与投顾内容由内置模拟数据 + 启发式规则生成，已在代码中预留接入真实 LLM 与行情数据的扩展点，便于后续替换为生产数据源。

## ⚠️ 许可证

内部演示项目，私有使用。
