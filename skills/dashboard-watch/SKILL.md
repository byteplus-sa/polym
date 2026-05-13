---
name: dashboard-watch
version: 0.1.0
description: "通过客户名 + 具体需求查询 C360 数据看板，呈现用量趋势和洞察。触发词：'查一下客户X的数据'、'dashboard watch'、'X用了多少tokens'、'看一下X的用量'。"
metadata:
  requires:
    bins: ["lark-cli"]
    chrome_extension: true
---

# dashboard-watch — 客户数据看板查询

通过客户名称 + 具体问题，查询 C360 用量数据，并将有价值的洞察保存到知识库。

## 触发场景

- "查一下 Acme 的数据"
- "X 上个月用了多少 tokens"
- "看一下 X 的用量趋势"
- "dashboard watch"
- "帮我拉一下 X 的 C360 数据"
- "X 的月度用量报告"

---

## 完整执行流程

### Phase 0 — 准备

**0.1 解析输入**

从用户请求中提取：
- `customer_name`：客户名称（必须）
- `query`：具体问题（可选，默认：近 30 天用量概览）
- `date_range`：时间范围（可选，默认：近 30 天）

如果 `customer_name` 不明确，直接问：「你想查哪个客户的数据？」

**0.2 本地 wiki 解析（按 `core/local-wiki-ux.md` 标准）**

同 im-digest Phase 0.2 流程：env → 记忆 → 探测 → 询问（只问一次）。

**0.3 检查 Chrome 扩展**

C360 查询通过 Claude in Chrome 扩展进行浏览器自动化。

检查方式：
```
尝试调用 mcp__Claude_in_Chrome__list_connected_browsers
```

- **扩展已连接**：显示已连接浏览器列表，继续
- **扩展未安装 / 未连接**：进入 § Chrome 扩展安装引导

---

## Chrome 扩展安装引导

当扩展不可用时，向用户展示：

```
需要安装 Claude for Chrome 扩展才能查询 C360 数据。

安装步骤（约 2 分钟）：

1. 打开 Chrome，访问：
   https://chromewebstore.google.com/detail/claude/...
   （或在 Chrome 扩展商店搜索 "Claude"）

2. 点击「添加到 Chrome」→「添加扩展程序」

3. 点击 Chrome 右上角扩展图标，固定 Claude 扩展

4. 在扩展中点击「Connect to Claude Code」
   （确保 Claude Code 正在运行）

5. 安装完成后告诉我，我来继续查询。
```

等待用户回复「好了」或「安装完了」，然后重新检查并继续。

---

### Phase 1 — 查询 C360

使用 c360-customer-usage skill 的浏览器自动化流程（读取 `~/.claude/skills/c360-customer-usage/SKILL.md`）。

**标准查询内容：**

```
1. 日活跃用量（Daily tokens / API calls）— 近 30 天
2. 月度 MoM 对比
3. 主要使用产品分布
4. 用量峰值日期和原因（如有）
5. 当前余额 / quota 状态
```

**针对用户具体问题补充查询**（如有）：
- "用了多少 tokens" → 精确数字 + 趋势图截图
- "环比增长了吗" → MoM % 变化
- "主要在用什么功能" → 产品维度拆分
- "还有多少余额" → 当前 quota / 余额

---

### Phase 2 — 生成洞察

数据拿到后，沿以下维度识别洞察（只报告显著的）：

| 洞察类型 | 触发条件 | 建议行动 |
|---|---|---|
| **用量增长** | MoM > +30% | 了解增长原因，判断是否需要扩容 |
| **用量下降** | MoM < -20% | ⚠️ 风险信号，主动联系确认 |
| **用量骤停** | 最近 7 天接近 0 | 🚨 紧急，可能出问题了 |
| **quota 告急** | 余额 < 20% | 提醒客户续费或申请扩容 |
| **用量集中** | 单日用量 > 月均 3× | 了解是什么场景（大批量任务？压测？） |
| **新产品启用** | 某产品首次出现用量 | 了解使用场景，支持上手 |

---

### Phase 3 — 输出报告

在终端输出：

```
📊  <客户名> · 数据报告（<日期范围>）

用量概览
  近 30 天总用量：<N> tokens
  日均：<n> tokens
  MoM：<+/-N%>（<上月> → <本月>）

产品分布
  <Product A>：<N%>
  <Product B>：<N%>

Quota 状态
  当前余额：<N>（<X%> remaining）
  预计耗尽：<日期 or "充足">

<如有洞察>
⚠️  洞察：<洞察描述>
    建议：<行动建议>
```

**如果识别到有价值的洞察（用量下降、骤停、quota 告急等），询问用户：**

「发现了一些值得关注的数据，要保存到知识库吗？[Y/n]」

- Y / 直接回车：进入写入流程
- N：结束，不写入

> 注意：纯数字查询（"X 用了多少 tokens"）不触发询问，直接报告数字即可。

---

### Phase 4 — 写入知识库

**仅当用户确认有价值的洞察需要保存时执行。**

**本地 wiki（静默）：**

更新 `wiki/entities/customers/<slug>.md`：
- `## Recent interactions` 追加一行：「<TODAY> · 数据看板 · <一句话洞察>」
- 如有用量下降/骤停 → `## Open feedback / pain points` 标注风险

**Lark wiki（via sa-wiki WRITE workflow）：**

- APPEND TIMELINE：「<TODAY> | dashboard | <洞察摘要> | quota: <状态>」
- 如有 quota 告急 → CREATE/APPEND 相关提醒

写入时不向用户暴露写入细节，完成后在报告末尾显示 `已保存到知识库`。

---

### Phase 5 — 收尾

```
✅  <客户名> 数据查询完成

<洞察摘要（如有）>

<如有写入>已保存到知识库（<proposal_id>）
```

---

## 安全规则

- C360 数据不包含具体合同金额，但如有单价/ARR 数字，不写入 wiki（只做口头报告）
- 浏览器会话完成后不留存截图文件
- 不直接 `docs +update` wiki 页面

## 参考文档

- [`references/c360-query.md`](references/c360-query.md)
- [`core/local-wiki-ux.md`](../../core/local-wiki-ux.md)
