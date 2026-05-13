---
name: customer-brief
version: 0.1.0
description: "会前客户情报快照：输入客户名，30 秒内生成可以直接去开会的 2 分钟快报。触发词：'帮我备一下 X 的课'、'customer brief X'、'X 的客户情报'、'开会前看一下 X'。"
metadata:
  requires:
    bins: ["lark-cli"]
---

# customer-brief — 会前客户情报

**只读技能**：聚合现有数据源生成情报快照，不触发任何 wiki 写入。

## 触发场景

- "帮我备一下 Acme 的课"
- "customer brief Acme"
- "开会前看一下 Acme 的情况"
- "Acme 的客户情报"
- "给我一份 X 的 brief"
- "我要去见 X 了，帮我准备一下"

## 参数

```
customer-brief <客户名>                 # 默认：14 天动态 + 3 路查询
customer-brief <客户名> --quick         # 只查 wiki，~5 秒
customer-brief <客户名> --full          # 4 路含 C360，~20 秒
customer-brief <客户名> --days 7        # 自定义动态时间窗口（默认 14）
customer-brief <客户名> --date tomorrow # 指定会议日期（影响建议措辞）
```

---

## 执行流程

### Phase 0 — 解析输入

从用户输入提取：
- `CUSTOMER`：客户名（必须）。如果不明确，问：「你想查哪个客户？」
- `DAYS`：动态时间窗口（默认 14）
- `MODE`：quick / default / full（默认 default）
- `MEETING_DATE`：会议日期（默认 today）

计算时间窗口：
```bash
# macOS
WINDOW_START=$(date -v-${DAYS}d +%Y-%m-%d)
TODAY=$(date +%Y-%m-%d)
START_TIME="${WINDOW_START}T00:00:00+08:00"
END_TIME="${TODAY}T23:59:59+08:00"
```

**本地 wiki 路径解析**（按 `core/local-wiki-ux.md`）：env → 记忆 → 探测。找不到则跳过本地查询，不询问（brief 是读操作，不强制创建 wiki）。

---

### Phase 1 — 4 路并发查询

**在同一个消息里发出所有 Agent 调用**（并发，不串行）。

#### 查询 ① — SA Wiki（必须）

```
Agent(
  subagent_type="general-purpose",
  description="Query SA Wiki for customer",
  prompt="""
    Query the SA Wiki Bitable for customer: <CUSTOMER>

    Constants (from sa-wiki SKILL.md §3):
    BASE_TOKEN=UXPdbPJ3kaheZvs2Nc8lLGCcglh
    KI_TABLE=tblLKeA8N3ipyEQv

    Steps:
    1. Search knowledge_index for this customer:
       lark-cli base +record-search --base-token $BASE_TOKEN --table-id $KI_TABLE \
         --json '{"filter":{"conjunction":"and","conditions":[
           {"field_name":"Customer","operator":"is","value":["<CUSTOMER>"]}
         ]},"page_size":50}' --format json --as user

    2. From results, identify and fetch (in parallel if possible):
       - PROFILE doc (lark-cli docs +fetch --api-version v2 --doc <token> --as user)
       - TIMELINE doc (most recent 10 entries)
       - Any open feedback pages (status=open or in-progress)

    Return structured JSON:
    {
      "found": true/false,
      "profile": { stage, region, industry, account_owner, lark_chat, products_in_play[], key_contacts[] },
      "recent_timeline": [ { date, type, summary } ],  // last 10 entries
      "open_feedback": [ { title, priority, status, product } ],
      "commitments": []  // items we committed to (from TIMELINE/interactions)
    }
    Return under 400 words. If not found, return {"found": false}.
  """
)
```

#### 查询 ② — 本地 Wiki（如有 LOCAL_WIKI_ROOT）

```
Agent(
  subagent_type="general-purpose",
  description="Query local wiki for customer",
  prompt="""
    Read local wiki at <LOCAL_WIKI_ROOT> for customer: <CUSTOMER>

    Steps:
    1. Find customer file: <LOCAL_WIKI_ROOT>/wiki/entities/customers/<slug>.md
       (try slug variations: lowercase-kebab of <CUSTOMER>)
    2. Read the file. Extract:
       - status, lark_chat
       - ## Products in play
       - ## Recent interactions (entries within last <DAYS> days)
       - ## Open feedback / pain points
    3. Also check wiki/sources/ for recent chat/meeting files for this customer
       (files matching: *<customer-slug>* with date within last <DAYS> days)
       Extract TL;DR bullets from each.

    Return structured JSON:
    {
      "found": true/false,
      "status": "...",
      "lark_chat": "...",
      "recent_interactions": [ { date, type, summary } ],
      "open_pain_points": [ "..." ],
      "recent_source_tldr": [ "..." ]
    }
    Return under 300 words. If customer not found locally, return {"found": false}.
  """
)
```

#### 查询 ③ — 近期 IM（default + full 模式）

```
Agent(
  subagent_type="general-purpose",
  description="Search recent Lark IM for customer",
  prompt="""
    Search Lark messages for customer: <CUSTOMER>
    Time range: <START_TIME> to <END_TIME>

    Steps:
    1. Find the chat_id for this customer (use lark_chat from wiki if available,
       otherwise: lark-cli im +chat-search --keyword "<CUSTOMER>" --as user)
    2. Fetch recent messages:
       lark-cli im +chat-messages-list \
         --chat-id <oc_xxx> \
         --start "<START_TIME>" --end "<END_TIME>" \
         --sort asc --page-size 50 --format json --as user
    3. Filter noise (short messages, emoji, "好的/收到")
    4. Extract: customer feedback, feature asks, risk signals, competitor mentions,
       unanswered questions

    Return structured JSON:
    {
      "found": true/false,
      "message_count": N,
      "last_active": "YYYY-MM-DD",
      "highlights": [
        { "date": "MM-DD", "type": "feedback|ask|risk|competitor|decision", "summary": "..." }
      ],
      "unanswered_questions": [ "..." ],
      "risk_signals": [ "..." ],
      "competitor_mentions": [ { "name": "...", "context": "..." } ]
    }
    Return under 300 words. If chat not found, return {"found": false}.
  """
)
```

#### 查询 ④ — C360 用量（full 模式，且 Chrome 扩展已就绪）

仅在 `--full` 且 `mcp__Claude_in_Chrome__list_connected_browsers` 返回非空列表时触发。

```
Agent(
  subagent_type="general-purpose",
  description="Query C360 usage for customer",
  prompt="""
    Query C360 for customer: <CUSTOMER>
    Use the dashboard-watch skill and c360-customer-usage skill pattern.
    Read ~/.claude/skills/c360-customer-usage/SKILL.md for browser automation steps.

    Extract:
    - Last 30 days total usage + daily average
    - MoM % change
    - Quota remaining %
    - Main product by usage %

    Return structured JSON:
    {
      "found": true/false,
      "monthly_tokens": N,
      "mom_pct": "+/-N%",
      "quota_remaining_pct": N,
      "top_product": "...",
      "alert": null | "quota_low" | "usage_drop" | "usage_stop"
    }
    Return under 150 words.
  """
)
```

---

### Phase 2 — 等待并汇聚结果

等所有 agent 返回（或超时 30 秒）。**不等 ④ 阻塞 ①②③**。

用汇聚逻辑（见 [`references/query-strategy.md`](references/query-strategy.md)）合并去重：
- 同一事件在 wiki 和 IM 都出现 → 保留一条，优先用 wiki 描述（更精炼）
- 冲突信息（wiki 和 IM 不一致）→ 以 IM 为准（更新），标注 `[wiki 可能过时]`

---

### Phase 3 — 规则引擎：生成"建议今天聊"

基于汇聚结果，按以下规则确定性生成建议（不是 AI 自由发挥）：

```
优先级规则（按序检测，取前 3 条有触发的）：

P0 — 必说（总是排第一）：
  - Quota remaining < 20%  → "确认 quota 续费方案"
  - 有未响应的客户提问（距今 > 3 天）→ "回复 X 的问题"
  - 有明确风险信号（"换一家"/"考虑别家"）→ "了解并回应竞品考虑"

P1 — 重要（如有则提）：
  - 有过期承诺（我方承诺 > 7 天未跟进）→ "同步 [承诺内容] 进展"
  - 有 open feedback P0/P1 且 > 14 天无更新 → "更新 [feedback名] 状态"
  - 用量下降 MoM < -20% → "了解用量下降原因"
  - 出现竞品提及 → "准备针对 [竞品名] 的差异化"

P2 — 有就提：
  - 有未确认的 Feature ask → "确认 [ask] 的优先级/时间线"
  - 产品更新或新功能 → "介绍最新 [产品] 进展"
```

---

### Phase 4 — 输出 Brief

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  <CUSTOMER> — 会前情报  <TODAY>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【速览】
  阶段: <stage> | 产品: <products> | 负责人: <account_owner>
  上次接触: <N天前>（<type>）| 关键联系人: <name, role>

【近期动态】  最近 <DAYS> 天
  <MM-DD>  <type>  <summary>
  <MM-DD>  <type>  <summary>
  ...（最多 6 条，按时间倒序）

【未关闭事项】                     （空则隐藏）
  ⚠️  <quota/risk>
  ❓  <unanswered question>
  📋  <open feedback title>（<priority>）

【我们的承诺】                      （空则隐藏）
  → <commitment>（<date> 承诺，已过 <N> 天）

【竞品雷达】                        （空则隐藏）
  <competitor>：<context>（<date>）

【建议今天聊】
  1. <rule-driven suggestion>
  2. <rule-driven suggestion>
  3. <rule-driven suggestion>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
数据来源: <标注哪几路有数据>  |  模式: <quick/default/full>
```

如果某个 section 完全没有内容，整块隐藏（不显示空标题）。

---

### Phase 5 — 可选后续动作

Brief 输出后，提示可用的快速操作：

```
需要更多信息？
  • 输入 "deep dive" 获取完整 wiki 档案
  • 输入 "recent meetings" 查看最近会议详情
  • 输入 "C360" 拉取用量数据（如未显示）
```

---

## 安全规则

- 纯读操作，不写任何 wiki 或 write_queue
- 不展示合同金额，用量数字以趋势（+/-N%）为主
- 客户 PII（手机/邮件）不在摘要中显示，但在详情中可查

## 参考文档

- [`references/query-strategy.md`](references/query-strategy.md)
- [`core/local-wiki-ux.md`](../../core/local-wiki-ux.md)
- sa-wiki SKILL.md §3（Bitable 常量）
- sa-wiki SKILL.md §4（READ workflow）
