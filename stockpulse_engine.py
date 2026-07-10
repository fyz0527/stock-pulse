# -*- coding: utf-8 -*-
"""
智讯股研 StockPulse AI — 核心引擎（演示版 / 可运行）
=====================================================
本文件用纯 Python 标准库实现 PRD 的核心逻辑：
  1. 五档情绪判定（启发式，标注为 LLM 接入点）
  2. 受影响 A 股映射（知识图谱 + 规则 + LLM 隐式推理的占位）
  3. 个人投顾量价技术分析（持仓/买入/卖出/留底仓卖出）

注意：演示版用「关键词启发式」代替 LLM；生产环境在 classify_sentiment()
与 llm_infer_affected() 处接入真实大模型即可，接口保持一致。
"""
import json
from dataclasses import dataclass, field, asdict
from typing import Optional


# ---------------------------------------------------------------------------
# 1. 知识图谱（种子数据，对应深化文档 §3）
# ---------------------------------------------------------------------------
# 实体 -> 直接关联的 A 股（产业链/替代/供需/概念）
KG = {
    "英伟达": {"market": "美股", "alias": ["NVDA", "Nvidia", "英伟达"],
              "affects": [
                  ("300308", "中际旭创", "通信设备", "产业链下游", "GPU 算力扩张拉动 800G/1.6T 光模块(CPO)需求"),
                  ("300502", "新易盛", "通信设备", "产业链下游", "同属 AI 光模块核心供应商"),
                  ("300394", "天孚通信", "通信设备", "产业链下游", "光器件配套英伟达算力链"),
                  ("002384", "东山精密", "电子制造", "供应商客户", "PCB/精密制造供应 AI 服务器链"),
              ]},
    "AMD": {"market": "美股", "alias": ["AMD", "超威"],
            "affects": [
                ("688256", "寒武纪", "半导体", "国产替代", "AMD GPU 对标产品，国产 AI 芯片替代逻辑"),
                ("603986", "兆易创新", "半导体", "国产替代", "存储/MCU 国产替代受益"),
            ]},
    "美光": {"market": "美股", "alias": ["MU", "Micron", "美光"],
             "affects": [
                 ("603986", "兆易创新", "半导体", "国产替代", "美光受限制则国产存储替代加速"),
                 ("300223", "北京君正", "半导体", "国产替代", "车规/利基存储国产替代"),
             ]},
    "海力士": {"market": "日韩", "alias": ["SK Hynix", "SK하이닉스", "海力士"],
               "affects": [
                   ("603986", "兆易创新", "半导体", "概念板块", "HBM/存储涨价周期带动存储板块"),
                   ("688008", "澜起科技", "半导体", "概念板块", "存储接口芯片受益"),
               ]},
    "三星": {"market": "日韩", "alias": ["Samsung", "三星电子", "三星"],
             "affects": [
                 ("000725", "京东方A", "面板", "同业竞争", "面板价格与产能联动"),
                 ("603986", "兆易创新", "半导体", "概念板块", "存储芯片涨价指引利好板块"),
             ]},
    "英特尔": {"market": "美股", "alias": ["INTC", "Intel", "英特尔"],
               "affects": [
                   ("688256", "寒武纪", "半导体", "国产替代", "x86 弱势利好国产 CPU/GPU"),
                   ("603986", "兆易创新", "半导体", "国产替代", "国产芯片替代逻辑"),
               ]},
    "康宁": {"market": "美股", "alias": ["GLW", "Corning", "康宁"],
             "affects": [
                 ("300433", "蓝思科技", "电子制造", "供应商客户", "玻璃基板/盖板供需联动"),
             ]},
    "长江存储": {"market": "概念", "alias": ["YMTC", "长江存储"],
                 "affects": [
                     ("603986", "兆易创新", "半导体", "概念板块", "长江存储扩产利好存储芯片概念"),
                     ("300223", "北京君正", "半导体", "概念板块", "存储国产化概念"),
                 ]},
    "长鑫存储": {"market": "概念", "alias": ["CXMT", "长鑫存储"],
                 "affects": [
                     ("603986", "兆易创新", "半导体", "概念板块", "长鑫 DRAM 国产替代概念"),
                     ("688008", "澜起科技", "半导体", "概念板块", "DRAM 接口芯片配套"),
                 ]},
    "中际旭创": {"market": "A股", "alias": ["300308", "中际旭创"],
                 "affects": [("300308", "中际旭创", "通信设备", "直接", "事件主体即为 A 股标的")]},
    "东山精密": {"market": "A股", "alias": ["002384", "东山精密"],
                 "affects": [("002384", "东山精密", "电子制造", "直接", "事件主体即为 A 股标的")]},
    "寒武纪": {"market": "A股", "alias": ["688256", "寒武纪"],
               "affects": [("688256", "寒武纪", "半导体", "直接", "事件主体即为 A 股标的")]},
    "兆易创新": {"market": "A股", "alias": ["603986", "兆易创新"],
                 "affects": [("603986", "兆易创新", "半导体", "直接", "事件主体即为 A 股标的")]},
}

# 概念板块 -> 成员（对应规则 R-Concept）
CONCEPT = {
    "存储芯片": [("603986", "兆易创新"), ("300223", "北京君正"), ("688008", "澜起科技")],
    "算力/CPO": [("300308", "中际旭创"), ("300502", "新易盛"), ("300394", "天孚通信")],
    "半导体设备": [("688012", "中微公司"), ("002371", "北方华创")],
    "面板": [("000725", "京东方A")],
    "玻璃基板": [("300433", "蓝思科技")],
    "PCB": [("002384", "东山精密"), ("002916", "深南电路")],
    "券商": [("600030", "中信证券"), ("601211", "国泰君安")],
    "黄金": [("600547", "山东黄金"), ("002155", "湖南黄金")],
}

# 宏观/政策 -> 概念（对应规则 R-Macro）
MACRO = {
    "美联储": {"鸽派|降息|维持|偏鸽": ["券商", "黄金"], "加息|紧缩": ["黄金"]},
    "算力": {"补贴|政策": ["算力/CPO", "半导体设备"]},
    "出口管制": {"设备限制|管制": ["半导体设备"]},
}


# ---------------------------------------------------------------------------
# 2. 五档情绪判定（启发式；LLM 接入点）
# ---------------------------------------------------------------------------
SENTIMENT_RULES = [
    ("利好", ["创新高", "超预期", "大涨", "利好", "获大单", "扩产", "上调", "中标", "突破", "满产", "涨价", "补贴", "扶持"]),
    ("利空", ["制裁", "暴跌", "不及预期", "裁员", "减产", "下调", "亏损", "风险", "限制", "收紧"]),
    ("中性偏利好", ["略超预期", "小幅增长", "温和回暖", "偏正面", "略好于"]),
    ("中性偏利空", ["略不及预期", "小幅下滑", "温和承压", "偏负面", "略弱于"]),
    ("中性", ["符合预期", "平稳", "维持", "不变", "中性", "持平"]),
]


def classify_sentiment(text: str):
    """
    返回 (tier, confidence, summary_hint)
    —— 演示用关键词启发式；生产环境替换为 LLM 调用，保持同签名。
    """
    text = text or ""
    for tier, kws in SENTIMENT_RULES:
        for kw in kws:
            if kw in text:
                # 置信度按关键词强度给一个演示值
                conf = 0.85 if tier in ("利好", "利空") else 0.7 if "偏" in tier else 0.6
                return tier, conf, f"命中关键词「{kw}」"
    return "中性", 0.55, "无显著方向词，默认中性"


# ---------------------------------------------------------------------------
# 3. 受影响 A 股映射（对应深化文档 §5-§6）
# ---------------------------------------------------------------------------
def _find_entity(token: str):
    for name, node in KG.items():
        if token == name or token in node.get("alias", []):
            return name, node
    return None, None


def map_affected(event_title: str, event_body: str = ""):
    """
    六条映射规则（直接/产业链/替代/供需/概念/宏观）。
    返回 list[dict]，每条含 code,name,sector,relation,reason,conf。
    """
    text = f"{event_title} {event_body}"
    out = {}

    def add(code, name, sector, relation, reason, base_conf):
        if code not in out:
            out[code] = {"code": code, "name": name, "sector": sector,
                         "relation": relation, "reasons": [reason], "conf": base_conf}
        else:
            out[code]["reasons"].append(reason)
            out[code]["conf"] = min(1.0, out[code]["conf"] + 0.1)

    # 规则 1+4：实体直接命中 / 产业链 / 替代 / 供需
    for token in KG:
        ent, node = _find_entity(token)
        if ent and (token in text or any(a in text for a in node.get("alias", []))):
            for code, name, sector, rel, reason in node["affects"]:
                conf = 1.0 if rel == "直接" else 0.8 if rel in ("产业链下游", "供应商客户") else 0.6
                add(code, name, sector, rel, reason, conf)
            # 概念关键词展开（规则 R-Concept）
            for concept, members in CONCEPT.items():
                if concept in text:
                    for code, name in members:
                        add(code, name, "概念板块", "概念板块", f"事件涉及「{concept}」板块", 0.6)

    # 规则 6：宏观/政策
    for macro, sub in MACRO.items():
        if macro in text:
            for pattern, concepts in sub.items():
                import re
                if re.search(pattern, text):
                    for c in concepts:
                        for code, name in CONCEPT.get(c, []):
                            add(code, name, "概念板块", "宏观影响", f"「{macro}」事件映射至「{c}」板块", 0.5)

    # 合并理由
    result = []
    for code, v in out.items():
        result.append({
            "code": v["code"], "name": v["name"], "sector": v["sector"],
            "relation": v["relation"], "reason": "；".join(v["reasons"][:2]),
            "conf": round(v["conf"], 2),
        })
    result.sort(key=lambda x: x["conf"], reverse=True)
    return result


def llm_infer_affected(event_title: str, event_body: str = ""):
    """
    LLM 隐式推理占位（深化文档 §6）。
    生产环境：检索实体子图 + few-shot 让 LLM 假设候选，再 grounding 校验。
    演示版返回空，表示图谱已覆盖。
    """
    return []  # 接入真实 LLM 时实现


# ---------------------------------------------------------------------------
# 4. 个人投顾：量价技术分析（对应 PRD R9）
# ---------------------------------------------------------------------------
def analyze_holding(series, profile: dict):
    """
    series: list of {"close":float,"volume":float} （按时间升序）
    profile: {capital_tier, position_ratio, habit, learn_level}
    返回 {conclusion, suggestion, reason, note}
    """
    if len(series) < 6:
        return {"conclusion": "数据不足", "suggestion": "持仓",
                "reason": "样本不足，暂无法给出量价结论", "note": ""}
    closes = [s["close"] for s in series]
    vols = [s["volume"] for s in series]
    ma5 = sum(closes[-5:]) / 5
    ma10 = sum(closes[-10:]) / 10 if len(closes) >= 10 else closes[0]
    last, prev = closes[-1], closes[-2]
    price_chg = (last - prev) / prev
    vol_avg = sum(vols[-5:]) / 5
    vol_chg = (vols[-1] - vols[-2]) / vols[-2]

    # —— 量价关系判断（重点）——
    if price_chg > 0.01 and vol_chg > 0.2:
        conclusion = "放量上涨，量价齐升"
        suggestion = "买入"
        reason = f"价格 +{price_chg*100:.1f}% 且成交放量 +{vol_chg*100:.1f}%，资金主动上攻，趋势健康"
    elif price_chg < -0.01 and vol_chg > 0.2:
        conclusion = "高位放量下跌 / 放量滞涨"
        suggestion = "卖出"
        reason = f"价格 {price_chg*100:.1f}% 但成交放量 +{vol_chg*100:.1f}%，获利盘出逃，警惕转弱"
    elif price_chg < 0 and vol_chg < -0.2:
        conclusion = "缩量回调"
        if last > ma10:
            suggestion = "买入"
            reason = f"缩量回调 {price_chg*100:.1f}%，未破 MA10({ma10:.2f})，属良性整理可低吸"
        else:
            suggestion = "留底仓卖出"
            reason = f"缩量回调且跌破 MA10({ma10:.2f})，短线走弱但中线逻辑在，减仓留底仓"
    elif abs(price_chg) <= 0.01 and vol_chg > 0.3:
        conclusion = "平量滞涨（量价背离）"
        suggestion = "留底仓卖出"
        reason = "价格走平但异常放量，筹码松动，建议兑现部分利润保留底仓"
    elif vols[-1] < vol_avg * 0.6:
        conclusion = "地量见底"
        suggestion = "持仓"
        reason = "成交极度萎缩，抛压枯竭，可观望等待方向选择"
    else:
        conclusion = "量价配合平稳"
        suggestion = "持仓"
        reason = f"价格在 MA5({ma5:.2f})/MA10({ma10:.2f}) 间震荡，量能平稳，持有待变"

    # 结合个人画像备注
    note = (f"结合您{profile.get('capital_tier','')}资金体量、"
            f"当前仓位{profile.get('position_ratio','')}、"
            f"{profile.get('habit','')}风格")
    if profile.get("learn_level") == "新手":
        note += "，建议小仓位验证、严格止损"
    return {"conclusion": conclusion, "suggestion": suggestion,
            "reason": reason, "note": note}


# ---------------------------------------------------------------------------
# 5. 演示
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("智讯股研 StockPulse AI — 引擎演示")
    print("=" * 60)

    sample_events = [
        ("英伟达数据中心收入创新高，上调全年指引", "利好"),
        ("美光遭某国出口限制，存储供给收紧", "利空(对美光)/利好(国产替代)"),
        ("三星电子存储芯片涨价指引超预期", "利好"),
        ("英特尔宣布大规模裁员，战略收缩", "利空"),
        ("美联储维持利率不变，表态偏鸽", "中性偏利好"),
        ("国内算力补贴政策出台", "利好"),
    ]
    for title, expect in sample_events:
        tier, conf, hint = classify_sentiment(title)
        affected = map_affected(title)
        print(f"\n【事件】{title}")
        print(f"  情绪: {tier} (置信度 {conf}, {hint}) | 预期: {expect}")
        print(f"  受影响 A 股 ({len(affected)}):")
        for a in affected[:5]:
            print(f"    - {a['name']}({a['code']}) [{a['relation']}] conf={a['conf']} :: {a['reason']}")

    # 个人投顾演示
    print("\n" + "=" * 60)
    print("个人投顾量价分析演示（持仓：中际旭创）")
    print("=" * 60)
    # 构造一段放量上涨的模拟序列
    mock_series = [{"close": 100 + i, "volume": 1000 + i * 20} for i in range(10)]
    mock_series[-1]["close"] = 112
    mock_series[-1]["volume"] = 1500
    profile = {"capital_tier": "中户", "position_ratio": "60%", "habit": "中线", "learn_level": "进阶"}
    r = analyze_holding(mock_series, profile)
    print(f"  结论: {r['conclusion']}")
    print(f"  建议: {r['suggestion']}")
    print(f"  原因: {r['reason']}")
    print(f"  个性化备注: {r['note']}")
