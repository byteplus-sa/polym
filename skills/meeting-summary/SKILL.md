---
name: meeting-summary
version: 0.1.0
description: "整理一段时间内的所有会议（飞书 VC + 妙记），提取客户洞察和重要结论，自动保存到知识库。触发词：'整理最近的会议'、'meeting summary'、'帮我总结一下昨天的会'、'会议纪要整理'。"
metadata:
  requires:
    bins: ["lark-cli"]
---

# meeting-summary — 会议内容整理

把一段时间内的所有飞书会议编译成结构化知识，自动保存到知识库。

## 触发场景

- "整理最近的会议"
- "帮我总结一下昨天的会"
- "meeting summary"
- "会议纪要整理"
- "整理一下 [时间范围] 的会议"

## 依赖

- `lark-cli`（vc 模块 + minutes 模块）
- 本地 wiki（路径自动解析，见 Phase 0）
- Lark wiki 写入委托给 **sa-wiki skill**

---

## 完整执行流程

### Phase 0 — 准备

**0.1 确定时间范围**

默认：昨天 00:00 到现在。

```bash
# macOS
YESTERDAY=$(date -v-1d +%Y-%m-%d)
START_TIME="${YESTERDAY}T00:00:00+08:00"
NOW=$(date -u +"%Y-%m-%dT%H:%M:%S+08:00")

# Linux
YESTERDAY=$(date -d yesterday +%Y-%m-%d)
```

如果用户指定了时间范围（"上周的会议"、"5月10日到12日"），按用户指定解析。

**0.2 本地 wiki 解析（按 `core/local-wiki-ux.md` 标准）**

1. 检查 `LOCAL_WIKI_ROOT` 环境变量
2. 查 Claude 记忆系统中 `local-wiki-root` 记忆
3. 自动探测：`~/sa-wiki`、`~/wiki`、`~/LLM-Wiki`
4. 全部未找到 → 询问一次：「还没有本地 wiki，要创建一个吗？[Y/n]」
   - Y：「保存在哪里？（回车默认 ~/sa-wiki）」→ 调用 `local-wiki-init` → 保存到记忆
   - N：本次跳过本地写入

---

### Phase 1 — 发现会议

**1.1 查询飞书 VC 历史会议**

```bash
lark-cli vc +meetings-list \
  --start-time "$START_TIME" \
  --end-time "$NOW" \
  --format json --as user
```

**1.2 查询飞书妙记**

```bash
lark-cli minutes +list \
  --start-time "$START_TIME" \
  --end-time "$NOW" \
  --format json --as user
```

合并两个来源，去重（同一会议可能同时出现在 VC 和妙记里），按开始时间升序排列。

展示会议列表（标题、时间、时长），如果有未参加的会议，标注 `[未参与]`，仍处理（有妙记的情况下）。

---

### Phase 2 — 获取每场会议内容

**对每场会议**，按优先级获取内容：

**优先：飞书妙记 AI 产物（最结构化）**

```bash
# 获取会议总结
lark-cli minutes +get-summary --token <minute_token> --as user

# 获取章节（带时间戳的分段）
lark-cli minutes +get-chapters --token <minute_token> --as user

# 获取待办
lark-cli minutes +get-todos --token <minute_token> --as user
```

**次选：飞书妙记逐字稿**

```bash
lark-cli minutes +get-transcript --token <minute_token> --as user
```

**兜底：VC 会议详情**

```bash
lark-cli vc +meeting-detail --meeting-id <meeting_id> --as user
```

对于只有 VC 记录、没有妙记的会议：仅记录基础信息（参会人、时长），标注 `[无录音/纪要]`。

---

### Phase 3 — 分析提炼

对每场会议，沿以下维度提炼（无内容则跳过）：

| # | 维度 | 说明 |
|---|---|---|
| 1 | **会议目的** | 这场会开的是什么，一句话 |
| 2 | **关键结论** | 达成的共识、做的决定，过去时声明式 |
| 3 | **客户反馈** | 正面/负面，具体产品/功能 |
| 4 | **Feature Asks** | 客户明确提出的需求 |
| 5 | **技术问题** | 报错、集成难点、API 问题 |
| 6 | **商务进展** | 合同、续费、POC 里程碑（金额不入 wiki） |
| 7 | **竞品信号** | 提及竞品及对比评价 |
| 8 | **⚠️ 风险信号** | 流失风险、强烈不满、deadline 压力 |
| 9 | **待跟进** | 有人提到但没解决，或我方承诺但未交付 |
| 10 | **参会人** | 客户侧关键人（姓名、角色）|

**跨会议聚合**（所有会议处理完后）：
- 同一客户的多场会议 → 合并到一个客户摘要
- 同一问题在多场会议出现 → 跨会议洞见

---

### Phase 4 — 输出摘要

在终端输出结构化摘要：

```markdown
# 会议摘要 — <YESTERDAY> → <NOW 时间>

共 <N> 场会议 · <M> 场有妙记

---

## <客户名> · <会议标题> · <HH:MM>（<时长>min）

### 关键结论
- <past-tense decision>

### 客户反馈
- <feedback>

### Feature Asks
- 「<ask>」— <who>，产品：<product>

### ⚠️ 风险信号
- <signal>

### 待跟进
- <item>

---

## [无妙记] <会议标题> · <时间>
参会人：<N> 人 · 时长：<M> min · 无纪要记录

---

## 跨会议洞见
- <insight>（涉及 <N> 场会议）
```

**输出完成后直接写入，不询问用户。**

---

### Phase 5 — 写入本地 wiki（静默）

**仅当 LOCAL_WIKI_ROOT 有效时，静默执行。**

对每场有内容的会议：

1. **创建 source 页面** `wiki/sources/meeting-<slug>-<DATE>.md`
2. **更新客户页面** `wiki/entities/customers/<slug>.md`：
   - `## Recent interactions` 追加一行 + 链接到 source 页
   - 新 Feature ask → `## Open feedback` 添加链接
   - 商务进展 → 更新 `status` frontmatter（如有变化）
   - 风险信号 → `## Open feedback / pain points` 标注
3. 如有新参会人 → 创建/更新 `wiki/entities/people/<slug>.md`
4. 更新 `wiki/index.md` + 追加 `wiki/log.md`

---

### Phase 6 — 写入 Lark wiki

**自动执行，使用 sa-wiki skill §5 WRITE workflow。**

- 每个有内容的客户 → APPEND TIMELINE
- Feature Asks → CREATE/APPEND feedback 页面
- 技术问题 → CREATE/APPEND error-code 页面
- 风险信号 → APPEND TIMELINE（标注风险标签）
- 写入前执行脱敏（`META_DESENSITIZATION`，由 sa-wiki 管理）

---

### Phase 7 — 收尾报告

```
✅  会议整理完成（<YESTERDAY> → 现在）

<N> 场会议 · <M> 场有妙记 · <K> 个客户有更新

摘要：
  关键结论：<N> 条
  Feature asks：<N> 条
  竞品信号：<N> 条
  ⚠️ 风险信号：<N> 条（建议跟进：<客户名>）

已保存 <K> 条到知识库（<proposal_ids>）
```

---

## 安全规则

- 会议内容不写合同金额，用 "price discussed"
- 脱敏由 sa-wiki 负责
- 只写入自己参加或有妙记权限的会议
- 不写 `docs +update` 直接操作 wiki 页面

## 参考文档

- [`core/local-wiki-ux.md`](../../core/local-wiki-ux.md)
- [`references/meeting-fetch.md`](references/meeting-fetch.md)
