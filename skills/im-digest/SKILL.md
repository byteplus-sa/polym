---
name: im-digest
version: 0.3.0
description: "拉取昨天的 Lark IM 消息，整理 topics 和重点内容，自动保存到知识库。触发词：'整理昨天的消息'、'daily IM digest'、'拉一下昨天的群消息'、'im digest'。"
metadata:
  requires:
    bins: ["lark-cli"]
---

# im-digest — 昨日 IM 消息整理

每天把 Lark 群聊里的信息编译成结构化知识，自动保存。

## 触发场景

- "整理昨天的消息"
- "拉一下昨天的群消息"
- "daily IM digest"
- "im digest"
- "帮我总结一下昨天的 IM"
- "把昨天的聊天记录整理进知识库"

## 依赖

- `lark-cli`（im 模块）
- 本地 wiki（路径自动解析，见 Phase 0）
- Lark wiki 写入委托给 **sa-wiki skill**

---

## 完整执行流程

### Phase 0 — 准备

**0.1 计算时间范围**

```bash
# macOS
YESTERDAY=$(date -v-1d +%Y-%m-%d)
START_TIME="${YESTERDAY}T00:00:00+08:00"
END_TIME="${YESTERDAY}T23:59:59+08:00"

# Linux
YESTERDAY=$(date -d yesterday +%Y-%m-%d)
```

**0.2 本地 wiki 解析（按 `core/local-wiki-ux.md` 标准）**

1. 检查 `LOCAL_WIKI_ROOT` 环境变量
2. 查 Claude 记忆系统中是否有 `local-wiki-root` 记忆
3. 自动探测常见路径：`~/sa-wiki`、`~/wiki`、`~/LLM-Wiki`
4. 若全部未找到 → 询问一次：「还没有本地 wiki，要创建一个吗？[Y/n]」
   - Y：「保存在哪里？（回车默认 ~/sa-wiki）」→ 调用 `local-wiki-init` → 保存路径到记忆
   - N：本次跳过本地写入，记住偏好

**0.3 确定要扫描的聊天**

1. 从 `$LOCAL_WIKI_ROOT/wiki/entities/customers/*.md` 读取 `lark_chat` 字段
2. 用 `lark-cli im +chat-search --keyword <name>` 补充未记录的客户聊天
3. 用户可追加聊天名称 / chat_id

展示将扫描的聊天列表，等待确认。

---

### Phase 1 — 拉取消息

```bash
lark-cli im +chat-messages-list \
  --chat-id <oc_xxx> \
  --start "$START_TIME" --end "$END_TIME" \
  --sort asc --page-size 50 --format json --as user
```

`has_more=true` 时分页（上限 10 页 / 500 条）。

原始消息写入：`$LOCAL_WIKI_ROOT/raw/chat-<slug>-<YESTERDAY>.md`（如有本地 wiki）

---

### Phase 2 — 12 维分析

见 [`references/digest-schema.md`](references/digest-schema.md)：

| # | 维度 |
|---|---|
| 1 | 重点内容 |
| 2 | 客户反馈 — 正面 |
| 3 | 客户反馈 — 负面 |
| 4 | Feature Asks |
| 5 | 技术问题 & 报错 |
| 6 | 商务进展 |
| 7 | 竞品信号 |
| 8 | ⚠️ 风险信号 |
| 9 | 用量 & 配额 |
| 10 | 人员 & 组织变动 |
| 11 | 产品理解偏差 |
| 12 | 决策 & 待跟进 |

---

### Phase 3 — 输出 Digest

在终端输出结构化摘要（格式见 `references/digest-schema.md` § Output Format）。

**输出完成后直接进入写入阶段，不询问用户。**

---

### Phase 4 — 写入本地 wiki（静默）

**仅当 LOCAL_WIKI_ROOT 有效时执行，不告知用户正在写入。**

遵守 `$LOCAL_WIKI_ROOT/SCHEMA.md`：raw 不可编辑、双向关系、绝对日期、无 todos。

1. 更新 `wiki/entities/customers/<slug>.md`（Recent interactions、Products in play、Open feedback）
2. 创建 `wiki/sources/chat-<slug>-<YESTERDAY>.md`
3. 更新 `wiki/index.md` + 追加 `wiki/log.md`

---

### Phase 5 — 写入 Lark wiki

**自动执行，使用 sa-wiki skill §5 WRITE workflow，不告知用户"正在双写"。**

读取 `~/.claude/skills/sa-wiki/SKILL.md` §5，按其流程：
- APPEND TIMELINE（每个有内容的客户）
- CREATE/APPEND feedback / error-code 页面（Feature Ask、技术问题）
- 风险信号 → APPEND TIMELINE 并标注风险标签
- 写入前自动执行脱敏（`META_DESENSITIZATION`，由 sa-wiki 管理）

---

### Phase 6 — 收尾报告

```
✅  昨日（<YESTERDAY>）IM 整理完成

扫描 <N> 个聊天 · <M> 条有效消息

摘要：
  客户反馈：<N> 条  Feature asks：<N> 条
  竞品信号：<N> 条（客户：<A>, <B>）
  ⚠️ 风险信号：<N> 条（建议主动跟进：<客户名>）

已保存 <K> 条到知识库（<proposal_ids>）
```

风险信号客户单独高亮，方便 SA 优先处理。

---

## 安全规则

- 不直接 `docs +update` wiki 页面，全部经 sa-wiki write_queue
- 脱敏由 sa-wiki 负责（`META_DESENSITIZATION`）
- Raw 快照只读
- 只处理群聊，不处理 P2P 消息

## 参考文档

- [`references/fetch-workflow.md`](references/fetch-workflow.md)
- [`references/digest-schema.md`](references/digest-schema.md)
- [`core/local-wiki-ux.md`](../../core/local-wiki-ux.md)
