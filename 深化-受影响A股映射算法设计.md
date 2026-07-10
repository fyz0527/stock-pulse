# 深化设计（一）：受影响 A 股映射算法设计
## 对应 PRD R4 — 将跨市场事件映射到"受影响 A 股"清单

> 目标：给定一条已结构化的跨市场事件（美股/日韩/A股原发），自动产出**受影响 A 股列表**，每条含代码、名称、所属板块、关联类型、关联理由、置信度。核心诉求是"可解释、可追溯、高召回"。

---

## 1. 设计原则

1. **可解释优先**：每支标的必须附带一条人类可读的关联理由，禁止"黑箱罗列"。
2. **知识图谱为骨，LLM 为脑**：确定性关系走图谱（可审计、低幻觉）；隐性/新型关系由 LLM 推理并回锚图谱校验。
3. **召回与精度平衡**：核心产业链事件召回 ≥80%；宁可多列并降权，也不漏掉关键标的。
4. **非上市实体走概念**：长江存储/长芯等未上市公司，不虚构代码，按"概念板块"映射到相关 A 股。
5. **置信度透明**：每条映射带 0–1 置信度，前端据此排序与折叠。

---

## 2. 整体架构（流水线）

```
事件 Event
  │  {entities[], market, body, summary, sentiment}
  ▼
[Stage 1] 实体链接 Entity Linking
  │  提及 → 规范实体（公司/行业/概念/宏观），含别名词典 + LLM 兜底
  ▼
[Stage 2] 关系解析 Relation Resolution（图谱遍历）
  │  四类确定性关系 → 候选 A 股节点
  ▼
[Stage 3] LLM 隐式推理 Implicit Inference
  │  图谱未覆盖时，LLM 基于上下文 + 检索到的图谱子图 假设候选
  ▼
[Stage 4] 校验与去幻 Grounding & Validation
  │  LLM 候选 ∩ 图谱/A股全集；剔除不存在/无关标的
  ▼
[Stage 5] 置信度评分 & 排序 Scoring
  ▼
[Stage 6] 理由生成 & 去重 Explanation
  │  生成关联理由；同标的多路径合并
  ▼
输出 affectedStocks[]
```

---

## 3. 知识图谱 Schema

**节点（Node）**
| 类型 | 属性 |
|---|---|
| Company | id, name, aliases[], market(A/US/JP/KR), sector, concepts[], listed(bool) |
| Concept | id, name（如 "存储芯片""CPO""PCB"） |
| MacroEvent | id, name（如 "美联储加息""出口管制"） |

**边（Edge）**
| 类型 | 含义 | 方向 |
|---|---|---|
| `SUPPLIES_TO` | 供应商→客户 | A→B |
| `UPSTREAM` / `DOWNSTREAM` | 产业链上下游 | A–B |
| `COMPETES_WITH` | 同业竞争 | A–B |
| `SUBSTITUTES` | 替代关系（国产替代） | A–B |
| `HAS_CONCEPT` | 公司属于概念板块 | Company→Concept |
| `AFFECTS` | 宏观/政策影响行业 | MacroEvent→Concept/Sector |

**数据来源（默认假设）**
- 种子：同花顺/东方财富概念板块成员、上市公司年报产业链披露、公开产业链图谱。
- 维护：周期性刷新概念成员；新增上市公司自动入图；人工纠错日志回流。

---

## 4. 实体链接（Stage 1）

- 别名词典：NVDA↔英伟达；Hynix↔海力士↔SK하이닉스；中际旭创↔300308 等。
- 多语言：日/韩源先做翻译（R1 链路）再链接。
- LLM 兜底：未命中词典的实体，由 LLM 判定其规范名与所属市场/行业。
- 输出：规范实体列表，带 `entity_type`。

---

## 5. 关系解析与映射规则（Stage 2）

对 Stage1 的每个实体，按类型展开：

| 规则 | 触发 | 映射逻辑 | 示例 |
|---|---|---|---|
| R-Direct | 实体本身是 A 股 | 直接返回 | 中际旭创 → 中际旭创 |
| R-Chain | 产业链上下游 | 沿 UPSTREAM/DOWNSTREAM 取 N 跳（默认 1–2 跳）A 股节点 | 英伟达 →（下游 CPO）→ 中际旭创、新易盛 |
| R-Substitute | 海外同业受挫/受限 | 取 SUBSTITUTES / 国产替代概念 A 股 | 美光受制裁 → 国产存储（兆易创新、北京君正） |
| R-Supply | 供应商/客户依赖 | 沿 SUPPLIES_TO 取 A 股供应商或客户 | 苹果 → A 股果链（立讯、歌尔） |
| R-Concept | 概念/行业关键词 | 经 HAS_CONCEPT 展开概念全部 A 股成员 | "HBM" → 存储芯片概念成员 |
| R-Macro | 宏观/政策事件 | 经 AFFECTS 映射到受影响行业概念 | 美联储加息 → 券商/银行/黄金/有色概念 |

**跳数控制**：默认 1 跳（直接关联），重要产业链允许 2 跳；2 跳以上仅作低置信候选。

---

## 6. LLM 隐式推理 + Grounding（Stage 3–4）

当事件语义超出图谱覆盖（如"某新规利好液冷""某新药获批"）：
1. 检索与事件实体相关的图谱子图（邻居概念/公司）作为上下文。
2. LLM 基于 `{事件摘要 + 子图 + 示例 few-shot}` 假设 3–8 支候选 A 股，并给出暂定理由。
3. **Grounding 校验**：候选必须 ∈ A 股全集（代码有效），否则丢弃；理由必须能映射到已知关系或概念，否则标注"弱关联"。
4. 低置信候选折叠展示，不进入主列表强推。

> 防幻觉关键：LLM 只"建议在图中已存在的节点"，不生成图中没有的股票。

---

## 7. 置信度评分（Stage 5）

`confidence = w1·relationStrength + w2·sentimentStrength + w3·sourceReliability + w4·pathHitRate`

| 因子 | 取值 | 权重(默认) |
|---|---|---|
| 关系强度 relationStrength | 直接=1.0，1跳=0.8，2跳=0.5，概念=0.6，LLM弱关联=0.3 | 0.40 |
| 情绪强度 sentimentStrength | |sentiment| 映射 0–1（利好/利空强=1，中性偏=0.6，中性=0.2） | 0.25 |
| 来源可靠 sourceReliability | 公告/官方=1，权威媒体=0.8，其他=0.6 | 0.15 |
| 路径历史命中 pathHitRate | 该关系路径历史被人工确认比例 | 0.20 |

- 排序：按 confidence 降序；前端默认展示 Top N（如 8），其余"展开更多"。
- 阈值：confidence < 0.35 不进入主列表（仅存于后台）。

---

## 8. 输出、理由与去重（Stage 6）

- 同标的被多路径命中 → 合并，理由拼接（"产业链下游 + 概念成员"），置信度取路径最大值并轻微加权。
- 理由模板：
  - 产业链：`{海外实体} 的 {业务} 变动，通过 {上游/下游} 传导至 {A股}（{细分环节}）`
  - 替代：`{海外同业} 受 {事件}，国产替代利好 {A股}`
  - 概念：`事件涉及 {概念}，{A股} 为板块成员`
- 无映射：明确输出 `affectedStocks = []` 且标注"暂无直接 A 股影响标的"。

---

## 9. 评测方法

- **标注集**：人工标注 200–500 条代表性事件 → (事件, 黄金 A 股集合)。
- **指标**：Recall@K（K=5/8/10）、Precision@K、MRR。
- **目标**：核心产业链事件 Recall@8 ≥ 80%；整体 Precision@8 ≥ 70%。
- **回归**：每次图谱/提示词变更跑回归，防精度退化。
- **线上监控**：用户对"无关标的"的折叠/举报率作为负向信号回流。

---

## 10. 冷启动与持续维护

- 冷启动：先以"概念板块展开 + 头部产业链词典"覆盖高频事件，LLM 兜底长尾。
- 维护：周级概念成员刷新；用户纠错（"这条不该关联 X"）进入反馈队列，人工确认后写回图谱/惩罚路径权重。
- 版本化：图谱快照 + 模型版本绑定，保证结果可复现。

---

## 11. 边界与异常

| 场景 | 处理 |
|---|---|
| 非上市公司（长江/长鑫） | 不生成代码，按概念映射相关 A 股并标注"概念映射" |
| 宏观泛事件 | 经 AFFECTS 映射行业概念，避免个股误伤 |
| 多实体冲突 | 分别展开后合并去重，置信度独立 |
| LLM 给出图中无股票 | Grounding 阶段丢弃 |
| 映射为空 | 显式"暂无直接 A 股影响标的"，不假装 |

---

## 12. 关键伪代码

```python
def map_affected(event):
    entities = entity_linking(event)              # Stage1
    candidates = []
    for e in entities:
        candidates += graph_expand(e, max_hop=2)  # Stage2 R-Direct..R-Macro
    llm_cands = llm_infer(event, subgraph(entities))  # Stage3
    llm_cands = [c for c in llm_cands if c in A_SHARE_UNIVERSE]  # Stage4 grounding
    candidates += llm_cands
    scored = [(s, score_confidence(s, event)) for s in candidates]
    scored = dedupe_merge(scored)                 # Stage6
    scored = [s for s in scored if s.conf >= 0.35]
    scored.sort(by='conf', desc=True)
    return build_explanations(scored)             # Stage6
```
