---
name: sa-wiki
version: 1.0.0
description: "BytePlus SA Team 知识库（SA Wiki）查询与写入。当用户询问 SA 知识 / SA wiki / 我们的知识库 / 客户档案 / 客户会议纪要 / 帮我把这条信息归档到 wiki / 查一下我们对客户 X 的进展 / 添加一篇 topic 文档 / 整理一下这次会议纪要进 wiki / 把这个 handbook 章节 ingest 进来 等场景时使用。Read 路径走 Bitable knowledge_index 检索后 docs +fetch 全文；Write 路径强制走 02 · DATA / write_queue 表（Agent 不直接写 Wiki 页）。涉及多 Agent 并发安全。"
metadata:
  requires:
    bins: ["lark-cli"]
---

# SA Wiki — Knowledge Base Skill

> **前置条件：** 先阅读 [`../lark-shared/SKILL.md`](../lark-shared/SKILL.md)（认证、`--as user` 默认）和 [`../lark-base/SKILL.md`](../lark-base/SKILL.md)（Bitable 操作）。

SA Team 共享知识库，多 Agent 并发安全。**Read 直查 Bitable + 全文 fetch；Write 强制走 write_queue 队列**——Agent 永远不直接写 Wiki 页面。

## 1. 何时使用本 Skill

### 1.1 触发场景（任一即触发）

- "查一下 SA wiki / 我们的知识库 / 这个客户的情况"
- "我们对 X（客户）有什么了解"、"X 最近的进展"
- "把这次会议纪要整理进 wiki"
- "新建一篇 topic 文档"、"加一条 SOP / FAQ"
- "整理一下这条 chat 内容进知识库"
- "添加 handbook 章节到 sources"
- "查一下 access / security / product 相关的 SA 知识"
- "AK/SK 怎么轮换"、"Babi SSO 已知问题" 等具体业务问题

### 1.2 不应使用的场景

- 用户只是要读某个具体 Lark 文档（→ `lark-doc`）
- 用户直接给出 Bitable URL 要操作（→ `lark-base`）
- 用户在群里发消息（→ `lark-im`）
- 用户问开发者后台 / scope 管理（→ `lark-shared`）

## 2. 架构（一定要先理解）

### 2.1 三层 Karpathy 架构

```
sources/      Layer 1  原始素材（不可变；handbook / 妙记原始 / 聊天导出 / 政策原文）
   ↓ ingest
topics/  +  customers/   Layer 2  蒸馏知识 + 客户档案（Agent 高频读）
   ↓ query
回答 → 沉淀新洞见 → 走 write_queue 回写新页面（compound）
                       ↓
               LOG 表 append 一行
```

**关键不变量：**
- `sources/` 永不修改，只 ADD
- 写入唯一入口是 `write_queue`，不可绕开
- 每次写入由 coordinator 串行 commit + 写 log

### 2.2 物理结构

```
SA-Wiki (space_id=7636607758988626894)
├── 00 · README              schema / 多 Agent 协议
├── 01 · INDEX               docx 主导航（指向 Bitable views）
├── 02 · DATA                Bitable，3 张表 + 多个 view
├── 03 · sources/            handbook / meetings-raw / chat-archives / policy-docs
├── 04 · topics/             access / security / products / poc-playbook / onboarding / operations
├── 05 · customers/          每客户一个子树：PROFILE / TIMELINE / meetings / poc / issues / decisions
└── 06 · meta/               desensitization / glossary / lint / retention / page-templates
```

## 3. 常量（直接复制使用）

```bash
# Wiki
WIKI_SPACE_ID="7636607758988626894"
WIKI_README_NODE="B5UewSWRRiKtFJkxBxlcz8yFnn8"
WIKI_INDEX_NODE="MatBwo7VKiso8hkm7hqc0S5dnjg"
WIKI_SOURCES_NODE="OSLgwQk5hicApHkwD9XcQuJHneb"
WIKI_TOPICS_NODE="FRFxwalKRiZEpnkANdJcGEvGnpf"
WIKI_CUSTOMERS_NODE="SaGKw2s5tixMHkkQGEGcE1oAnKf"
WIKI_META_NODE="CPDNw6y2LiufkskbSfBcQwnzn7b"

# Bitable
BASE_TOKEN="UXPdbPJ3kaheZvs2Nc8lLGCcglh"
KI_TABLE="tblLKeA8N3ipyEQv"     # knowledge_index
WQ_TABLE="tblTR65mRdvE74Lu"     # write_queue
LOG_TABLE="tblcMspJB6BvWcoX"    # log

# Wiki meta pages (live source of truth — fetch these before writing)
META_PAGE_TEMPLATES="AK56dDr5ooxg7WxWQI2lT8D9gfg"
META_DESENSITIZATION="PAkrdxuhFocKKgxH8ABlGLOng3b"
META_GLOSSARY="K5r6d0ww6oCr9bxGWH7lG8AEgLe"
META_LINT_CHECKLIST="SjLQdZPu2o9yfAxIleDljr3ZgVf"
META_RETENTION_RULES="RTxYdKqnxodWvcxqDjRl4bqdgpf"

# knowledge_index views (Layer / Domain / All)
VIEW_ALL="vewHanmc0S"           # All — sorted by Updated
VIEW_TOPICS="vewKdnHaJf"
VIEW_CUSTOMERS="vewFNHm7XG"
VIEW_SOURCES="vew0Iqi4ro"
VIEW_META="vewUf8Zhfm"
VIEW_DOM_ACCESS="vewiU5R87h"
VIEW_DOM_SECURITY="vewLyVIqW5"
VIEW_DOM_PRODUCT="vewqXXrbwB"
VIEW_DOM_POC="vewEswsVw8"
VIEW_DOM_OPS="vew37R6Xqz"
VIEW_DOM_ONBOARDING="vewCnhCxk3"

# write_queue views
VIEW_WQ_PENDING="vewbiHHbfb"
VIEW_WQ_REJECTED="vew4BsGegp"
VIEW_WQ_COMMITS="vew54q677F"

# log views
VIEW_LOG_RECENT="vewv9zXG8S"
VIEW_LOG_BY_SA="vewIEpU2yt"
```

## 4. READ workflow（3 路并发 + 缺口反馈）

**核心原则**：知识查询不只查 SA Wiki，要并发查 **3 个数据源**，最后聚合结果。如果 SA Wiki 没有但其他源有，立刻反馈用户「这条要不要补到 wiki」——这是 compound 累积机制的入口。

### 3 个数据源

| 源 | 内容 | 工具 |
|---|---|---|
| 1️⃣ **SA Wiki**（自己的知识库） | 已沉淀的 topics / customers / sources | `lark-cli base +record-search` + `docs +fetch` |
| 2️⃣ **Lark Messages**（群聊 / 私聊历史） | 实时讨论、未沉淀的临时结论 | `lark-cli im +messages-search` |
| 3️⃣ **BytePlus Docs**（官方文档） | 产品 API、SDK、最新发布 | WebFetch `https://docs.byteplus.com/en/docs` |

### 实施：用 3 个并行 sub-agent

**强制：在同一个 message 里发出 3 个 Agent 调用**（不是串行 3 个），每个负责一个源：

```python
# Agent 1: SA Wiki
Agent(subagent_type="general-purpose",
      description="Search SA Wiki",
      prompt="Use sa-wiki skill query-workflow.md. Search SA Wiki for: '<query>'. ...")

# Agent 2: Lark Messages
Agent(subagent_type="general-purpose",
      description="Search Lark messages",
      prompt="Use lark-im skill. Search the user's recent messages and group chats for: '<query>'. ...")

# Agent 3: BytePlus Docs
Agent(subagent_type="general-purpose",
      description="Search BytePlus docs",
      prompt="WebFetch https://docs.byteplus.com/en/docs and search for: '<query>'. ...")
```

详细的子 agent prompt 模板见 [`references/query-workflow.md`](references/query-workflow.md)。

### 聚合 + 缺口反馈

3 路结果回来后：

1. **合成答案**：综合 3 个源给出最终回答
2. **检测缺口**：如果 (2) 或 (3) 有内容但 (1) Wiki 没有 → 主动告诉用户：

   > 「这个问题的答案我在 [Lark 群聊 / BytePlus 官方文档] 里找到了，但 SA Wiki 里没有相关页面。要不要让我提交一个 CREATE 提议到 write_queue，把这条沉淀进 wiki？」

3. 用户同意 → 走 [WRITE workflow](§5) 创建 topic 页面，source_refs 指向找到的 chat URL / doc URL

### 直接 Wiki 查询（已知是 wiki 内部问题）

某些场景明显只查 wiki 即可（例如「最近的 wiki 更新」、「客户 X 的 PROFILE」）——可以跳过 3 路并发：

```bash
# A. 关键词检索
lark-cli base +record-search --base-token $BASE_TOKEN --table-id $KI_TABLE \
  --json '{"keyword":"AK/SK","page_size":20}' --format json --as user

# B. 按 view 拉取
lark-cli base +record-list --base-token $BASE_TOKEN --table-id $KI_TABLE \
  --view-id $VIEW_DOM_ACCESS --limit 50 --format json --as user

# C. 拿到 doc_token 后读全文
lark-cli docs +fetch --api-version v2 --doc <doc_token> --as user
```

> ⚠️ Bitable 命令默认输出 markdown 表格。Agent 需要程序化解析时**必须加 `--format json`**。

**Agent 决策树：**
1. 是「查一个客户」？→ `record-search` 用 customer name 搜，或 `record-list` 走 `VIEW_CUSTOMERS` filter Customer
2. 是「查某个 domain」？→ `record-list` 走对应的 `VIEW_DOM_*`
3. 是「最近更新了什么」？→ `record-list` 走 `VIEW_ALL`（按 Updated desc 排序）
4. 是模糊问题？→ `record-search` 关键词搜，再读命中的全文

## 5. WRITE workflow（强制走 write_queue）

详细见 [`references/write-workflow.md`](references/write-workflow.md)。简版：

```bash
# Step 1: 拉最新脱敏规则（wiki 是真理之源，不要靠记忆）
lark-cli docs +fetch --api-version v2 --doc $META_DESENSITIZATION --as user
# Step 2: 拉对应 page template
lark-cli docs +fetch --api-version v2 --doc $META_PAGE_TEMPLATES --as user
# Step 3: 提交 write_queue 提议
lark-cli base +record-upsert --base-token $BASE_TOKEN --table-id $WQ_TABLE \
  --json '{
    "fields": {
      "agent_id": "<your_agent_id>",
      "action": "CREATE",
      "target_path": "topics/access/ak-sk-lifecycle",
      "content_md": "<full markdown body>",
      "source_refs": "<source URLs>",
      "status": "pending"
    }
  }' --as user

# Step 4: 拿到 proposal_id（P-XXXXX），告诉用户「已入队，等 coordinator commit」
# Step 5: 用户/coordinator 处理后状态变 committed / rejected
```

**4 种 action：**
- `CREATE` — 新建页面（target_path 必须按命名规范，target_doc_token 留空）
- `APPEND` — 追加到已有页面（target_doc_token 必填）
- `REPLACE` — 整体替换页面（target_doc_token 必填，慎用）
- `LINT` — 请求清理任务（自由 note，coordinator 处理）

## 6. 命名规范（必须严格遵守）

| 页面类型 | target_path 格式 |
|---|---|
| Topic | `topics/<domain>/<kebab-case-name>` |
| Customer profile | `customers/<customer-name>/PROFILE` |
| Customer timeline | `customers/<customer-name>/TIMELINE` |
| Meeting note | `customers/<customer-name>/meetings/<YYYY-MM-DD>-<slug>` |
| Customer issue | `customers/<customer-name>/issues/<YYYY-MM>-<slug>` |
| Customer decision | `customers/<customer-name>/decisions/<YYYY-MM-DD>-<slug>` |
| Source | `sources/<subfolder>/<descriptive-name>` |

**客户名**：默认真实名（如 `acme-corp`）；如 SA 要求匿名，按 SA 给的代号（如 `opn**art`）。映射不存 wiki。

## 7. 多 Agent 并发安全

- **读**：完全并发，无锁
- **写**：强制串行，全部走 `write_queue`
- **去重**：相同 `target_path` 的 pending 提议会被 coordinator 标 `superseded`
- **冲突**：REPLACE 操作 coordinator 校验 target 的 last_committed_at；冲突自动 reject
- **审计**：每条 commit 写入 `log` 表（含 SA 归属人 + agent_id + proposal_id）

## 8. 写入前必做：脱敏

**Wiki 是单一真理之源**——脱敏规则只在 wiki 维护，不在 skill 里复制：

```bash
lark-cli docs +fetch --api-version v2 --doc $META_DESENSITIZATION --as user
```

**任何 CREATE/APPEND/REPLACE 提议必须先过这个清单**，否则 coordinator 直接 reject。

红线速记（详细规则以 wiki 为准）：
- ❌ 实际 AK/SK / token / 密码值
- ❌ 客户 PII（姓名、电话、邮箱、ID 卡号、银行账户）
- ❌ 个人 SIP 金额、绩效分数
- ❌ L4 分级文档全文
- ❌ topics/ 页面里出现真实客户名（应该匿名为 [Customer A]）

## 9. Compound 原则

Karpathy 核心：**让查询产物沉淀回 wiki**。

如果 Agent 在查询过程中：
- 发现一个新的可泛化洞见（不属于任何现有 topic）→ 提议新建 topic 页
- 发现某个客户 issue 与已有 topic 关联 → 双向 link（在 customers/ 和 topics/ 各加链接）
- 发现现有页面有矛盾或缺漏 → 提交 LINT 提议

不要让有价值的回答消失在 chat 里。

## 10. References

**Skill 本地文件**（CLI 工作流，不会变化的）：

| 文件 | 内容 |
|---|---|
| [query-workflow.md](references/query-workflow.md) | 读取的完整决策树 + 命令模板 |
| [write-workflow.md](references/write-workflow.md) | 4 种 action 的完整步骤 + 错误处理 |
| [examples.md](references/examples.md) | 端到端示例：查客户、归档会议、新增 topic、报告 bug |

**Wiki 真理之源**（业务规则，会变化，每次写入前 fetch 最新）：

| 用途 | doc_token 常量 | fetch 命令 |
|---|---|---|
| 页面模板（7 种 page 类型） | `$META_PAGE_TEMPLATES` | `lark-cli docs +fetch --api-version v2 --doc $META_PAGE_TEMPLATES --as user` |
| 脱敏决策矩阵 | `$META_DESENSITIZATION` | `... --doc $META_DESENSITIZATION ...` |
| 受控词表 | `$META_GLOSSARY` | `... --doc $META_GLOSSARY ...` |
| 定期清理清单 | `$META_LINT_CHECKLIST` | `... --doc $META_LINT_CHECKLIST ...` |
| 内容保留规则 | `$META_RETENTION_RULES` | `... --doc $META_RETENTION_RULES ...` |

> ⚠️ Skill **不缓存** wiki 内容。每次写入前先 fetch，避免 stale。

## 11. 安全规则

- 默认 `--as user`，写入操作前必须确认用户意图
- 永远不直接 `docs +update` 修改 Wiki 页面（除非用户明确要求绕开 write_queue）
- 提交 write_queue 后告知用户 `proposal_id`，让用户能追溯
- 客户 sensitive 信息（合同金额、人事评价、矛盾细节）默认 `Sensitivity: Restricted`，coordinator 会 hold for review
