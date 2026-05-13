# Digest Schema — Analysis Dimensions & Output Format

## Analysis Dimensions

For each chat, extract content along these dimensions. Only include a dimension if there is genuine content — omit empty sections.

### 1. 重点内容（Key Points）
General noteworthy information. Always include if the chat had any meaningful messages.
- Decision made
- Significant status change
- Important context shared

### 2. 客户反馈（Customer Feedback）
Anything the customer said about their experience with BytePlus products.
- Positive feedback (what's working well)
- Negative feedback / complaints
- Specific bug reports

Extraction signals: "效果不错"、"有个问题"、"报错了"、"比 X 好"、"用不了"

### 3. Feature Asks
Explicit requests for new features, capabilities, or changes.
- "能不能支持 X"
- "希望有 Y 功能"
- "什么时候有 Z"

Capture: what was asked, who asked it, why (if stated).

### 4. 技术问题（Technical Issues）
API errors, integration problems, performance issues.
- Error codes / error messages
- SDK issues
- Configuration / auth problems

### 5. 达成的结论（Decisions / Commitments）
Anything that was agreed upon or committed to. Past tense, declarative.
- "我们下周发 X"（结论：X scheduled for next week）
- "先用 Y 方案"（结论：using Y approach）
- Demos scheduled, follow-ups confirmed

**Not** personal todos — only facts / decisions with product or customer relevance.

### 6. 待跟进（Pending Items）
Things that were raised but not resolved — not personal todos, but relationship/product-relevant open questions.
- Questions that went unanswered
- Issues flagged but not debugged yet
- Commitments made by us that haven't landed

---

## Signal-to-Noise Filter

**Include**: Messages with ≥ 15 characters containing product names, customer names, technical terms, questions, or explicit statements.

**Exclude**:
- Pure emoji / sticker messages
- "好的" / "收到" / "OK" / "👍" / "谢谢"
- Duplicate forwarded content (keep first occurrence)
- Bot-generated routine messages (standby alerts, auto-reminders) unless they indicate an incident
- Messages from before/after the time window (double-check timestamps)

---

## Output Format Template

```markdown
# IM Digest — <YESTERDAY>

> 扫描了 <N> 个聊天，共 <M> 条有效消息。有实质内容：<K> 个聊天。

---

## <客户名 / 聊天名>

**消息量**：<n> 条 · **活跃时段**：<HH:MM–HH:MM> · **chat_id**：<oc_xxx>

### 重点内容
- <bullet>

### 客户反馈
- <bullet>

### Feature Asks
- <bullet>（产品：<product>，优先级建议：P<N>）

### 技术问题
- <error_or_issue>（<sender>，<HH:MM>）

### 达成的结论
- <decision>（by <who>）

### 待跟进
- <item>

---

## <下一个聊天>

...

---

## 跨聊天洞见

> 只在 2+ 个聊天提到同一问题时生成。

- <insight>（涉及客户：<A>, <B>）

---

## 无实质内容的聊天

| 聊天 | 消息数 | 说明 |
|---|---|---|
| <name> | <n> | 全为打招呼/噪音 |
| <name> | 0 | 昨日无消息 |
```

---

## Categorization Decision Tree

```
Message received
    │
    ├── Length < 15 chars AND no product/customer name? → SKIP (noise)
    │
    ├── Contains error code / "报错" / stack trace? → Technical Issue
    │
    ├── Contains "能不能" / "希望" / "支持" / "功能" / "什么时候"? → Feature Ask
    │
    ├── Positive sentiment about product? → Customer Feedback (positive)
    │
    ├── Negative sentiment / complaint? → Customer Feedback (negative)
    │
    ├── Agreement / commitment / "就这样" / "定了" / "安排"? → Decision
    │
    ├── Question unanswered in the chat? → Pending
    │
    └── Other meaningful content? → Key Points
```

---

## Wiki Write Decision Tree

```
For each dimension extracted:

Customer Feedback
    → Inline bullet on customer wiki page (## Recent interactions)
    → If repeating across 2+ customers: create feedback-* page

Feature Ask
    → Check if feedback page exists for this ask
        Yes → APPEND to existing feedback page: add this customer to requesters
        No  → CREATE new feedback-<slug> page (kind: feedback)
    → APPEND customer TIMELINE in Lark wiki

Technical Issue
    → If it's a known error code: APPEND to existing error-code page
    → If new: CREATE error-code-<slug> page (kind: error-code)
    → Log on customer page under Recent interactions

Decision / Commitment
    → Inline on customer page (## Recent interactions)
    → If cross-entity: create interaction page in wiki/interactions/

Pending Item
    → Inline on customer page as a dated note
    → Do NOT create a todo or checkbox
```

---

## Sensitivity Check Before Any Write

Before writing to either wiki, verify the content does NOT contain:
- AK/SK / tokens / passwords (pattern: 32+ char alphanumeric strings)
- Customer PII (phone, ID number, email addresses — use [redacted] if needed)
- Contract dollar amounts (replace with "price discussed")
- Individual performance evaluations
- L4-classified content

If sensitive content is detected: redact in wiki copy, keep verbatim in raw/ only.
