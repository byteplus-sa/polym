---
name: im-digest
version: 0.2.0
description: "拉取昨天的 Lark IM 消息，整理 topics 和重点内容，同步写入本地 wiki（raw + wiki pages）和 Lark wiki（via sa-wiki）。触发词：'整理昨天的消息'、'daily IM digest'、'拉一下昨天的群消息'、'im digest'。"
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
- 本地 wiki（路径解析见 Phase 0.2）
- Lark wiki 写入完全委托给 **sa-wiki skill**（不重复其逻辑）

---

## 完整执行流程

### Phase 0 — 准备

**0.1 计算昨天的日期**

```bash
# macOS
YESTERDAY=$(date -v-1d +%Y-%m-%d)
START_TIME="${YESTERDAY}T00:00:00+08:00"
END_TIME="${YESTERDAY}T23:59:59+08:00"

# Linux
YESTERDAY=$(date -d yesterday +%Y-%m-%d)
```

**0.2 确定本地 wiki 路径（含记忆）**

按以下优先级依次检查，**找到即停止**：

1. **环境变量** `LOCAL_WIKI_ROOT`
2. **记忆系统** — 读取 `~/.claude/projects/*/memory/` 下是否有 `local-wiki-root.md`（或等效记忆文件），提取其中的路径
3. **常见路径自动探测**（依次检查是否存在）：
   - `~/sa-wiki`
   - `~/wiki`
   - `~/LLM-Wiki`
   - `~/Documents/sa-wiki`
4. **询问用户**（仅当以上全部失败）：
   > 「你的本地 wiki 在哪个目录？（例如 ~/sa-wiki）  
   > 输入路径，或直接回车跳过本地写入。」

**⚡ 如果用户提供了路径，立即写入记忆，避免下次重复提问：**

```
将以下内容写入记忆系统（使用 Write 工具）：
文件路径：<memory_dir>/local-wiki-root.md
---
name: local-wiki-root
description: User's local LLM wiki root directory path
type: user
---

Local wiki root: <用户输入的路径>

Set by user during im-digest setup on <TODAY>.
```

允许用户跳过本地写入（输入回车），此时只写 Lark wiki。

**0.3 确定要扫描的聊天**

优先级：
1. **本地 wiki 自动发现**：读取 `$LOCAL_WIKI_ROOT/wiki/entities/customers/*.md` 中的 `lark_chat` 字段
2. **搜索补充**：对未记录 `lark_chat` 的客户，用 `lark-cli im +chat-search --keyword <name>` 查找
3. **用户指定**：可额外添加聊天名称或 chat_id

展示将扫描的聊天列表，等待用户确认。

---

### Phase 1 — 拉取消息

对每个聊天，拉取昨日消息：

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

`has_more=true` 时分页，最多 10 页（500 条/聊天）。

原始消息保存到本地：`$LOCAL_WIKI_ROOT/raw/chat-<slug>-<YESTERDAY>.md`  
格式：`[HH:MM] <sender>: <content>`，媒体内容用占位符标注。

---

### Phase 2 — 12 维分析

对每个聊天提炼内容（详见 [`references/digest-schema.md`](references/digest-schema.md)）：

| # | 维度 | 提取内容 |
|---|---|---|
| 1 | **重点内容** | 当天最重要的 1–3 件事，必填 |
| 2 | **客户反馈 — 正面** | 称赞、满意、惊喜 |
| 3 | **客户反馈 — 负面** | 抱怨、Bug、体验差 |
| 4 | **Feature Asks** | 明确提出的功能/改进需求 |
| 5 | **技术问题 & 报错** | Error code、API 失败、集成难点 |
| 6 | **商务进展** | 合同、定价、续费、POC 里程碑、付款节点 |
| 7 | **竞品信号** | 提及 Runway / Pika / Kling / Sora / OpenAI 等，以及对比评价 |
| 8 | **风险信号** | 流失风险、不满、"考虑换一家"、deadline 压力 |
| 9 | **用量 & 配额** | quota 不够、用量突增、计费疑问 |
| 10 | **人员 & 组织变动** | 新联系人加入、决策人变化、团队重组 |
| 11 | **产品理解偏差** | 客户对功能/限制有误解，需后续澄清 |
| 12 | **决策 & 待跟进** | 已达成的结论（过去时），以及悬而未决的事项 |

**过滤噪音**：纯表情、"好的/收到/👍"、重复转发内容、bot 例行提醒。

---

### Phase 3 — 生成 Digest

在终端输出结构化摘要，格式见 [`references/digest-schema.md`](references/digest-schema.md) § Output Format。

输出后询问：「要把以上内容写入 wiki 吗？[Y/n]」（默认 Y）。

---

### Phase 4 — 写入本地 wiki

**仅当用户确认且有本地 wiki 路径时执行。**

遵守 `$LOCAL_WIKI_ROOT/SCHEMA.md` 的全部规则（raw 不可编辑、双向关系、绝对日期、禁止 todos）。

对每个有内容的聊天：

1. **更新客户页面** `wiki/entities/customers/<slug>.md`：
   - `## Recent interactions` 追加一行摘要 + source 链接
   - 新 Feature ask → 在 `## Open feedback` 添加链接
   - 新产品提及 → 更新 `## Products in play`（双向更新产品页面）
   - 商务进展 → 更新 `status` frontmatter（如有状态变化）
   - 风险信号 → 在 `## Open feedback / pain points` 标注

2. **创建 source 页面** `wiki/sources/chat-<slug>-<YESTERDAY>.md`（Source 模板）

3. **更新** `wiki/index.md` + **追加** `wiki/log.md`

---

### Phase 5 — 写入 Lark wiki

**完全委托给 sa-wiki skill，不在此重写逻辑。**

读取 sa-wiki skill 的 SKILL.md（`~/.claude/skills/sa-wiki/SKILL.md`）§5 WRITE workflow，按其流程操作：

1. **脱敏**：先 fetch `$META_DESENSITIZATION`，对整理内容逐项检查
2. **TIMELINE APPEND**：对每个有实质内容的客户，提交 APPEND 提议到 write_queue
3. **Feature Ask / 技术问题 / 风险信号**：对满足条件的内容提交 CREATE/APPEND 提议
4. **商务进展 / 竞品信号**：视内容重要性决定是否提交（由 agent 判断）

提交完成后，告知用户所有 `proposal_id`。

> ⚠️ 注意：sa-wiki write_queue 的 Bitable 常量、脱敏规则、page templates 均以 sa-wiki SKILL.md 为准，im-digest 不维护副本。

---

### Phase 6 — 收尾报告

```
✅  im-digest 完成 — <YESTERDAY>

本地 wiki（<LOCAL_WIKI_ROOT>）：
  更新客户页面：<N> 个
  新建 source 页面：<M> 个
  新建 feedback / error-code 页面：<K> 个

Lark wiki（write_queue via sa-wiki）：
  APPEND TIMELINE：<N> 条（proposal_id: P-xxxxx, ...）
  CREATE / APPEND 其他：<K> 条（proposal_id: P-xxxxx, ...）

维度汇总（昨日全局）：
  竞品信号：<N> 条（客户：<A>, <B>）
  风险信号：<N> 条（客户：<C>）
  Feature Asks：<N> 条

下一步：
  - 检查风险信号客户，考虑主动联系
  - 若有新 feedback 页面，补充 priority 字段
  - coordinator commit 后内容出现在 Lark wiki
```

---

## 安全规则

- Lark wiki 写入全部经过 sa-wiki write_queue，不直接 `docs +update`
- 写入前必须过 sa-wiki 的脱敏规则（`META_DESENSITIZATION`）
- Raw 快照只读，不可在后续步骤中修改
- 只处理群聊，不处理用户 P2P 消息

## 详细参考

- [`references/fetch-workflow.md`](references/fetch-workflow.md) — 消息拉取、分页、错误处理
- [`references/digest-schema.md`](references/digest-schema.md) — 12 维定义、信噪过滤、输出格式、wiki 写入决策树
