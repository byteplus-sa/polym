---
name: lark-doc-ingest
version: 0.1.0
description: "扫描一段时间内新增/修改的飞书文档，自动提炼并入库到知识库。默认范围：昨天 00:00 到现在。支持单篇文档指定入库。触发词：'把最近的文档入库'、'lark doc ingest'、'帮我整理一下最近的文档'、'把这个文档存进知识库'。"
metadata:
  requires:
    bins: ["lark-cli"]
---

# lark-doc-ingest — 飞书文档入库

扫描时间范围内的飞书文档，提炼关键内容，写入知识库。和 `im-digest` / `meeting-summary` 一样，自动保存，不打扰用户。

## 触发场景

- "把最近的文档入库"
- "帮我整理一下最近的文档"
- "把这个文档存进知识库"（同时提供 URL）
- "lark doc ingest"
- "ingest 一下昨天的 Lark 文档"

## 参数

```
lark-doc-ingest                          # 默认：昨天 00:00 到现在
lark-doc-ingest --url <lark-doc-url>     # 指定单篇文档
lark-doc-ingest --days 3                 # 自定义时间范围（天）
lark-doc-ingest --folder <folder-token>  # 限制到某个文件夹
lark-doc-ingest --dry-run                # 只显示会处理哪些文档，不实际写入
```

---

## 完整执行流程

### Phase 0 — 准备

**0.1 计算时间范围**

```bash
# macOS
YESTERDAY=$(date -v-1d +%Y-%m-%d)
START_TIME="${YESTERDAY}T00:00:00+08:00"
NOW=$(date +"%Y-%m-%dT%H:%M:%S+08:00")

# Linux
YESTERDAY=$(date -d yesterday +%Y-%m-%d)
```

用户指定 `--days N` 时：
```bash
START_TIME=$(date -v-${N}d +%Y-%m-%dT00:00:00+08:00)   # macOS
START_TIME=$(date -d "${N} days ago" +%Y-%m-%dT00:00:00+08:00)  # Linux
```

**0.2 本地 wiki 路径解析（按 `core/local-wiki-ux.md` 标准）**

env → 记忆 → 探测 → 询问一次（如果没有）。

**0.3 加载已知客户列表（用于分类）**

从本地 wiki 读取已知客户名：
```bash
grep -h "^# " $LOCAL_WIKI_ROOT/wiki/entities/customers/*.md 2>/dev/null \
  | sed 's/^# //'
```
同时读取 `aliases` frontmatter。这个列表用于后面的文档分类。

---

### Phase 1 — 发现文档

**指定单篇文档模式（`--url` 参数）**

直接跳到 Phase 2 处理该 URL，跳过发现步骤。

**默认模式：扫描时间范围内的文档**

并行执行两个搜索（合并去重）：

```bash
# 搜索 1：我最近编辑的文档
lark-cli drive +search --query "" \
  --edited-since "${YESTERDAY}" \
  --doc-types docx \
  --page-size 20 --format json --as user

# 搜索 2：最近新建的文档
lark-cli drive +search --query "" \
  --created-since "${YESTERDAY}" \
  --doc-types docx \
  --page-size 20 --format json --as user
```

如果用户指定了 `--folder`，两个命令都加 `--folder-tokens <folder-token>`。

**去重规则**：同一 `token` 只保留一条（两个搜索都返回的情况）。

**过滤——跳过以下文档：**

1. **已入库**：检查本地 wiki `$LOCAL_WIKI_ROOT/wiki/sources/` 目录中是否有 frontmatter 包含 `doc_id: <token>` 的文件
2. **标题黑名单**：标题匹配以下模式的跳过（可配置）：
   - 纯个人记录：`日记`、`today`、`日常`、`备忘`（仅标题完全是这些词）
   - 看起来是临时草稿：标题以 `草稿-`、`draft-`、`tmp-` 开头
3. **文档太短**：Phase 2 读取后内容 < 200 字（提炼无意义）

**展示将处理的文档列表**（如果多于 5 篇先列出，让用户确认或修改）：

```
发现 <N> 篇文档（<START_DATE> → 现在）

将处理：
  □ 《Acme POC 评估报告》       docx · 修改于 2026-05-12 15:30
  □ 《Seedance 竞品分析》        docx · 修改于 2026-05-12 10:00
  □ 《BytePlus 合规指南更新》    docx · 新建于 2026-05-12 09:00

将跳过（已入库）：
  ✓ 《Acme 需求文档 v2》        已于 2026-05-10 入库

继续？[Y/n]（默认 Y，5 秒无响应自动继续）
```

如果只有 1-3 篇文档，直接处理不询问。

---

### Phase 2 — 读取 & 分类（并行处理，每批最多 5 篇）

**对每篇文档：**

**Step A — 读取大纲**（低成本，先判断是否值得处理）

```bash
lark-cli docs +fetch --api-version v2 \
  --doc <token> --scope outline --as user
```

返回标题层级结构，不读全文。

**Step B — 分类**（基于标题 + 大纲）

```
分类逻辑：
1. 标题或 H1 包含已知客户名 / 客户 aliases → "客户文档"
2. 标题包含 BytePlus 产品名（Seedance / Seedream / ArkClaw / ARK / ...）→ "产品文档"
3. 标题包含竞品名（Runway / Pika / Kling / Sora / ...）→ "竞品文档"
4. 标题或 H1 包含"竞品"、"对比"、"vs"、"分析"→ "竞品/分析文档"
5. 有 "FAQ"、"指南"、"SOP"、"手册"→ "知识文档"
6. 其余 → "通用文档"
```

**Step C — 读取全文**（基于分类结果决定是否读）

跳过全文的情况：
- 内容大纲只有 3 行以下 AND 不含已知客户/产品 → 内容太少，跳过

其余情况读全文：
```bash
lark-cli docs +fetch --api-version v2 \
  --doc <token> --format pretty --as user
```

---

### Phase 3 — 提炼内容

对每篇已读取全文的文档，提炼以下信息：

| 提炼项 | 方法 |
|---|---|
| **TL;DR**（3-5 条） | 文档最重要的结论/内容 |
| **涉及客户** | 从内容中识别客户名（对照已知列表） |
| **涉及产品** | BytePlus 产品名称 |
| **涉及人员** | 姓名 + 角色（如有） |
| **Feature asks** | 客户明确提出的功能需求 |
| **决策/结论** | 文档中记录的决定 |
| **竞品信息** | 竞品提及和对比 |
| **商务信息** | 合同、定价相关内容（概述，不写具体金额） |

提炼后执行**脱敏检查**（参考 sa-wiki `META_DESENSITIZATION` 规则）：
- 移除 AK/SK、token、密码
- 替换客户 PII 为 [redacted]
- 合同金额替换为 "price discussed"

---

### Phase 4 — 写入本地 wiki（静默）

**仅当 LOCAL_WIKI_ROOT 有效时，静默执行。**

遵守 `SCHEMA.md`：raw 不可修改、双向关系、绝对日期。

**对每篇文档：**

1. **保存原始内容**（raw）：
   ```
   $LOCAL_WIKI_ROOT/raw/doc-<slug>-<YYYY-MM-DD>.md
   ```
   写入文档全文（已脱敏版本）。

2. **创建 source 页面** `wiki/sources/doc-<slug>-<DATE>.md`：
   ```markdown
   ---
   type: source
   kind: doc
   raw_path: raw/doc-<slug>-<DATE>.md
   customer: "[[<customer-slug>]]"   # 如有
   date: <DATE>
   url: <原始 Lark URL（去掉 disposable_login_token）>
   doc_id: <token>
   ---
   
   # <文档标题>
   
   ## TL;DR
   - <bullet>
   
   ## Extracted pages
   - [[<entity-slug>]]
   
   ## Verbatim quotes worth keeping
   > "<quote>"
   ```

3. **创建/更新实体页面**（如有涉及）：
   - 涉及客户 → 更新 `wiki/entities/customers/<slug>.md` 的 Sources 和 Recent interactions
   - 涉及产品 → 更新 `wiki/entities/products/<slug>.md`
   - Feature ask → 创建/更新 `wiki/concepts/feedback-<slug>.md`
   - 竞品信息 → 更新产品页面的 Related / Competition 部分

4. 更新 `wiki/index.md` + 追加 `wiki/log.md`

---

### Phase 5 — 写入 Lark wiki

**自动执行，使用 sa-wiki skill §5 WRITE workflow。**

对每篇有价值的文档（TL;DR 非空，有涉及客户/产品）：

- 若涉及客户 → APPEND 到 `customers/<slug>/TIMELINE`
- 若有 Feature ask → CREATE/APPEND feedback 页面
- 若有新知识（概念、SOP、产品功能解析）→ CREATE topic 页面
- 若是竞品文档 → APPEND 到对应产品页面的竞品部分

写入前自动执行 sa-wiki 的脱敏流程。

---

### Phase 6 — 收尾报告

```
📄  文档入库完成（<YESTERDAY> → 现在）

发现 <N> 篇 · 入库 <K> 篇 · 跳过 <M> 篇

入库详情：
  ✅ 《Acme POC 评估报告》    → 客户文档 · 更新 Acme 页面 + 新建 1 个 feedback
  ✅ 《Seedance 竞品分析》    → 竞品文档 · 更新 Seedance 产品页面
  ✅ 《BytePlus 合规指南》    → 知识文档 · 新建 topic 页面

跳过：
  ⏭️ 《今日备忘》            → 内容太短
  ⏭️ 《Acme 需求文档 v1》   → 已入库

已保存 <K> 条到知识库（<proposal_ids>）
```

---

## 安全规则

- 读取文档前不存储任何内容，fetch 失败不影响其他文档处理
- 脱敏在写入 wiki 前执行，原始内容仅保存在本地 `raw/`
- 不处理无 lark-doc 读取权限的文档（403 静默跳过，在报告中标注 `[无权限]`）
- 不直接 `docs +update` wiki 页面

## 参考文档

- [`references/doc-fetch-workflow.md`](references/doc-fetch-workflow.md)
- [`core/local-wiki-ux.md`](../../core/local-wiki-ux.md)
- sa-wiki SKILL.md §5（WRITE workflow）
