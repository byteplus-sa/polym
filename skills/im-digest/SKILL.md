---
name: im-digest
version: 0.1.0
description: "拉取昨天的 Lark IM 消息，整理 topics 和重点内容，同步写入本地 wiki（raw + wiki pages）和 Lark wiki（write_queue）。触发词：'整理昨天的消息'、'daily IM digest'、'拉一下昨天的群消息'、'im digest'。"
metadata:
  requires:
    bins: ["lark-cli"]
---

# im-digest — 昨日 IM 消息整理

每天把 Lark 群聊里的信息编译成结构化知识，写入本地 wiki 和 Lark wiki。

## 触发场景

- "整理昨天的消息"
- "拉一下昨天的群消息"
- "daily IM digest"
- "im digest"
- "帮我总结一下昨天的 IM"
- "把昨天的聊天记录整理进 wiki"

## 依赖

- `lark-cli`（im 模块）
- 本地 wiki（路径由 `LOCAL_WIKI_ROOT` 环境变量或用户输入决定）
- SA Wiki（Bitable 常量来自 sa-wiki skill）

## 完整执行流程

---

### Phase 0 — 准备

**0.1 计算昨天的日期**

```bash
# macOS
YESTERDAY=$(date -v-1d +%Y-%m-%d)
START_TIME="${YESTERDAY}T00:00:00+08:00"
END_TIME="${YESTERDAY}T23:59:59+08:00"

# Linux
YESTERDAY=$(date -d yesterday +%Y-%m-%d)
START_TIME="${YESTERDAY}T00:00:00+08:00"
END_TIME="${YESTERDAY}T23:59:59+08:00"
```

**0.2 确定本地 wiki 路径**

按优先级：
1. 环境变量 `LOCAL_WIKI_ROOT`
2. 用户在本次对话中提过的路径
3. 询问用户：「你的本地 wiki 在哪里？（如 ~/sa-wiki，或直接回车跳过本地写入）」

允许用户跳过本地写入（只写 Lark wiki）。

**0.3 确定要扫描的聊天**

优先级：
1. **从本地 wiki 自动发现**：读取 `$LOCAL_WIKI_ROOT/wiki/entities/customers/*.md` 中的 `lark_chat` 字段，收集所有已知客户聊天的 chat_id / chat name。
2. **搜索补充**：对没有记录 `lark_chat` 的客户或用户提到的聊天，用 `lark-cli im +chat-search --keyword <name>` 查找 chat_id。
3. **用户指定**：用户可额外指定聊天名称或 chat_id。

如果完全没有本地 wiki，询问用户要扫描哪些聊天（可输入名称或 chat_id，逗号分隔）。

展示将要扫描的聊天列表，等待用户确认（或 3 秒无响应自动继续）。

---

### Phase 1 — 拉取消息

**对每个确认的聊天**，执行：

```bash
lark-cli im +chat-messages-list \
  --chat-id <oc_xxx> \
  --start "$START_TIME" \
  --end "$END_TIME" \
  --sort asc \
  --page-size 50 \
  --format json \
  --as user
```

如果消息 > 50 条（has_more=true），继续分页直到取完。

**对每个聊天，把原始消息保存到本地**（如有本地 wiki）：
```
$LOCAL_WIKI_ROOT/raw/chat-<customer-slug>-<YESTERDAY>.md
```
格式：`[HH:MM] <sender>: <content>`，按时间升序，仅文字内容（图片/文件标注占位符）。

如果该 customer 的 raw 文件今天已存在，追加而不是覆盖。

---

### Phase 2 — 分析与整理

对每个聊天的消息，用以下标准提炼内容：

**提取维度**（见 [`references/digest-schema.md`](references/digest-schema.md)）：

| 维度 | 提取内容 |
|---|---|
| 客户反馈 | 客户对产品的评价、抱怨、惊喜 |
| Feature asks | 客户明确提出的功能需求或改进建议 |
| 技术问题 | 报错、API 问题、集成难点 |
| 决策 / 结论 | 双方达成的共识、确定的下一步 |
| 重要信息 | 上线节点、合同进展、竞品提及 |
| 待跟进 | 有人提到但还没结论的事项（不是个人 todo，是关系到客户/产品的事实） |

**过滤噪音**：
- 纯表情 / 点赞回应
- 「好的」「收到」「👍」等无实质内容的消息
- 重复转发同一内容

---

### Phase 3 — 生成 Digest

在终端输出结构化摘要（同时用于写入 wiki）：

```markdown
# IM Digest — <YESTERDAY>

> 扫描了 <N> 个聊天，共 <M> 条消息。有实质内容的聊天：<K> 个。

---

## <客户名 / 聊天名>

**消息量**：<N> 条 · **活跃时段**：<HH:MM–HH:MM>

### 重点内容
- <bullet>

### 客户反馈 / Feature asks
- <bullet（如有）>

### 技术问题
- <bullet（如有）>

### 达成的结论
- <bullet（如有）>

### 待跟进
- <bullet（如有）>

---

## 跨聊天洞见（可选）
如有多个客户提到同一问题/功能，在这里汇总。

---

## 无实质内容的聊天
<chat-name>：<N> 条，无有效信息（略）
```

输出后，询问用户：「要把以上内容写入 wiki 吗？[Y/n]」（默认 Y）。

---

### Phase 4 — 写入本地 wiki

**仅当用户确认且有本地 wiki 路径时执行。**

对每个有内容的聊天（对应一个客户）：

1. **创建或更新客户页面** (`wiki/entities/customers/<slug>.md`）：
   - 在 `## Recent interactions` 追加一行：
     `- <YESTERDAY> · chat · <一句话摘要> — [[chat-<slug>-<YESTERDAY>]]`
   - 如有新 Feature ask → 创建 `wiki/concepts/feedback-<slug>.md`，并在客户页面 `## Open feedback` 添加链接
   - 如有新产品提及 → 更新 `## Products in play`（双向更新产品页面）

2. **创建 source 页面** (`wiki/sources/chat-<slug>-<YESTERDAY>.md`）：
   ```markdown
   ---
   type: source
   kind: chat
   raw_path: raw/chat-<slug>-<YESTERDAY>.md
   customer: "[[<customer-slug>]]"
   date: <YESTERDAY>
   ---
   
   # chat-<slug>-<YESTERDAY>
   
   ## TL;DR
   <3–5 bullets from Phase 2>
   
   ## Extracted pages
   - [[<customer-slug>]]
   
   ## Verbatim quotes worth keeping
   > "<quote>" — <sender>
   ```

3. **更新 `wiki/index.md`**：在对应 section 追加新条目（如有新客户/产品/feedback）。

4. **追加 `wiki/log.md`**：
   ```markdown
   ## [<YESTERDAY>] ingest | im-digest (chat: <customer>)
   - Updated: [[<customer-slug>]]
   - Created: [[chat-<slug>-<YESTERDAY>]]（, [[feedback-<slug>]]）
   - Stubs: （如有）
   - Flagged: （cross-mentions 或矛盾）
   ```

遵守 `SCHEMA.md` 全部规则：raw 不可编辑、双向关系、绝对日期、禁止 todos。

---

### Phase 5 — 写入 Lark wiki（via sa-wiki write_queue）

**使用 sa-wiki skill 的常量**（从 sa-wiki SKILL.md §3 读取）：

```bash
BASE_TOKEN="UXPdbPJ3kaheZvs2Nc8lLGCcglh"
WQ_TABLE="tblTR65mRdvE74Lu"
KI_TABLE="tblLKeA8N3ipyEQv"
```

**对每个有实质内容的客户聊天**：

Step A — 查找客户 TIMELINE 的 doc_token：
```bash
lark-cli base +record-search \
  --base-token $BASE_TOKEN --table-id $KI_TABLE \
  --json '{"filter":{"conjunction":"and","conditions":[
    {"field_name":"Title","operator":"is","value":["customers/<slug>/TIMELINE"]}
  ]}}' --format json --as user
```

Step B — 如果 TIMELINE 存在，APPEND 一行：
```bash
lark-cli base +record-upsert \
  --base-token $BASE_TOKEN --table-id $WQ_TABLE \
  --json '{
    "fields": {
      "agent_id": "im-digest",
      "action": "APPEND",
      "target_path": "customers/<slug>/TIMELINE",
      "target_doc_token": "<TIMELINE_doc_token>",
      "content_md": "| <YESTERDAY> | chat | <一句话摘要> | [raw snapshot] |",
      "source_refs": "im-digest/<YESTERDAY>",
      "status": "pending"
    }
  }' --as user
```

Step C — 如有新 Feature ask / Pain-point，先脱敏检查，再 CREATE feedback 提议：
```bash
# 先拉最新脱敏规则
lark-cli docs +fetch --api-version v2 --doc $META_DESENSITIZATION --as user

# 提交 CREATE 提议
lark-cli base +record-upsert \
  --base-token $BASE_TOKEN --table-id $WQ_TABLE \
  --json '{
    "fields": {
      "agent_id": "im-digest",
      "action": "CREATE",
      "target_path": "topics/products/<feedback-slug>",
      "content_md": "<脱敏后内容>",
      "source_refs": "<chat 相关 Lark URL 或消息摘要>",
      "status": "pending"
    }
  }' --as user
```

Step D — 告知用户所有 proposal_id，方便追溯。

---

### Phase 6 — 收尾报告

```
✅  im-digest 完成 — <YESTERDAY>

本地 wiki（<LOCAL_WIKI_ROOT>）：
  更新客户页面：<N> 个
  新建 source 页面：<M> 个
  新建 feedback 页面：<K> 个

Lark wiki（write_queue）：
  APPEND TIMELINE：<N> 条（proposal_id: P-xxxxx, ...）
  CREATE feedback：<K> 条（proposal_id: P-xxxxx, ...）

下一步：
  - 检查 wiki/log.md 确认无误
  - 若有新 feedback 页面，补充 priority 字段
  - coordinator commit 后内容出现在 Lark wiki
```

## 安全规则

- 所有 Lark 写入均通过 write_queue，不直接 `docs +update` wiki 页面
- 写入前必须拉最新 `META_DESENSITIZATION` 并过滤：客户 PII、AK/SK、合同金额
- Raw 快照只读（不可在后续操作中修改）
- 用户 P2P 消息不纳入整理范围（只处理群聊）

## 详细参考

- [`references/fetch-workflow.md`](references/fetch-workflow.md) — 消息拉取、分页、错误处理
- [`references/digest-schema.md`](references/digest-schema.md) — 分析维度定义 + 输出格式模板
