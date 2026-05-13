# Digest Schema — 12 Analysis Dimensions & Output Format

## Analysis Dimensions

Extract along all 12 dimensions. Omit a section only if there is genuinely nothing to extract — don't force entries.

---

### 1. 重点内容（Key Points）
General noteworthy information. **Always include** for chats with any meaningful content.
- What was the most important thing that happened yesterday in this chat?
- 1–3 bullets max; must-reads for any SA who missed the day.

---

### 2. 客户反馈 — 正面（Positive Feedback）
Customer expressions of satisfaction, surprise, or appreciation.

Extraction signals: "效果不错"、"挺好的"、"比我想的好"、"满意"、"好用"、"准确"、"推荐"

Capture: what specifically impressed them, which product/feature.

---

### 3. 客户反馈 — 负面（Negative Feedback / Complaints）
Customer dissatisfaction, bugs, broken expectations.

Extraction signals: "有问题"、"报错了"、"效果差"、"用不了"、"比 X 差"、"不稳定"、"太慢"

Capture: what broke / disappointed, severity hint (blocking/annoying/minor).

---

### 4. Feature Asks（功能需求）
Explicit requests for features, capabilities, or behavioral changes.

Extraction signals: "能不能支持"、"希望有"、"什么时候有"、"能加一个"、"建议"

Capture: the ask verbatim or close paraphrase, who asked, why (if stated), which product.

---

### 5. 技术问题 & 报错（Technical Issues & Errors）
API errors, integration blockers, performance issues, configuration problems.

Extraction signals: error codes, stack traces, "API 返回"、"403"、"timeout"、"SDK"、"鉴权"

Capture: error code or description, context (what they were doing), whether it blocked them.

---

### 6. 商务进展（Business Progress）
Contract discussions, pricing negotiations, renewal signals, deal stage changes, payment nodes, POC milestones.

Extraction signals: "合同"、"续费"、"报价"、"付款"、"采购"、"审批"、"上线"、"milestone"、"预算"

Capture: what stage, any amounts (redact specifics — use "price discussed"), timeline.

> ⚠️ Sensitivity: DO NOT write dollar amounts to wiki. Use "price discussed" or "contract topic raised."

---

### 7. 竞品信号（Competitive Intelligence）
Mentions of competitors, comparisons, switching discussions.

Watch for: Runway, Pika, Kling, Sora, MidJourney, Stable Diffusion, OpenAI, Google Veo, Hailuo, Wan, Jimeng (即梦), Dreamina, Luma, ElevenLabs, and any "competitor" / "别家" / "换一个"

Capture: which competitor, in what context (comparison, switching threat, partnership), sentiment.

---

### 8. 风险信号（Churn / Risk Signals）
Signs that the customer relationship is at risk.

Extraction signals:
- Switching intent: "考虑换"、"试试别家"、"别家可以做"
- Strong dissatisfaction: repeated complaints, escalation language
- Deadline pressure: "必须下周"、"领导催"、"已经 delay 很久了"
- Ghosting reversal: "一直没消息，突然说..."
- Budget cut signals: "预算削减"、"暂停"

**Always flag for SA attention even if mild.** Better false positive than miss.

---

### 9. 用量 & 配额（Usage & Quota）
Quota issues, usage spikes, billing questions, cost concerns.

Extraction signals: "quota 不够"、"超额"、"用量"、"账单"、"充值"、"token"、"限制"

Capture: what limit was hit, impact on customer (blocked / slowed), what they need.

---

### 10. 人员 & 组织变动（Personnel & Org Changes）
New contacts joining, decision-maker changes, team restructuring, contact going silent.

Extraction signals: 新人 @, "新同事"、"换了负责人"、"原来的 XX 离职了"、"加了个 CTO"

Capture: who joined/left, their role, update the person page in wiki.

---

### 11. 产品理解偏差（Misunderstandings / Clarifications Needed）
Customer has an incorrect understanding of product capabilities, limitations, or roadmap.

Extraction signals:
- "我以为能..."（but actually can't）
- "你们说过..."（but that's not what was said）
- Asking for something that already exists
- Expecting a feature that's not on roadmap

Capture: what they misunderstood, what the correct understanding is, whether SA needs to follow up.

---

### 12. 决策 & 待跟进（Decisions & Pending Items）
**Decisions**: things that were agreed upon. Past tense, declarative.
- "就用方案 A"（decision: chose approach A）
- "下周 demo 定了"（decision: demo scheduled for next week）

**Pending**: raised but unresolved, product/relationship-relevant (not personal todos).
- Questions that went unanswered in the chat
- Issues flagged but not debugged yet
- Commitments we made that haven't landed

---

## Signal-to-Noise Filter

**Include**: Messages ≥ 15 chars with product names, customer names, technical terms, questions, or explicit statements.

**Exclude**:
- Pure emoji / sticker messages
- "好的" / "收到" / "OK" / "👍" / "谢谢" / "收到了"
- Duplicate forwarded content (keep first occurrence only)
- Bot routine alerts unless they signal an incident
- Off-topic small talk with no product/customer relevance

---

## Output Format Template

```markdown
# IM Digest — <YESTERDAY>

> 扫描 <N> 个聊天 · <M> 条有效消息 · 有内容 <K> 个

---

## <客户名 / 聊天名>

**消息量**：<n> 条 · **活跃时段**：<HH:MM–HH:MM> · **chat_id**：<oc_xxx>

### 重点内容
- <1–3 bullets>

### 客户反馈（正面）
- <bullet>（<sender>，<HH:MM>）

### 客户反馈（负面）
- <bullet>（<sender>，<HH:MM>，严重程度：blocking/annoying/minor）

### Feature Asks
- 「<原文或近似paraphrase>」— <who>，产品：<product>
  - 原因：<if stated>

### 技术问题 & 报错
- <error_code/description>（<sender>，<HH:MM>，是否阻塞：是/否）

### 商务进展
- <progress item>

### 竞品信号
- 提及 <competitor>：<context>（<sentiment: neutral/threat/comparison>）

### ⚠️ 风险信号
- <signal>（<sender>，<HH:MM>）— 建议跟进

### 用量 & 配额
- <quota_issue>

### 人员 & 组织变动
- <change>

### 产品理解偏差
- 误解：<what they think> → 实际：<correct understanding> — 需要澄清

### 决策 & 待跟进
**已决策：**
- <decision>（by <who>）

**待跟进：**
- <open item>

---

## 跨聊天洞见

> 仅在 2+ 个聊天出现同一模式时生成。

| 模式 | 涉及客户 | 严重程度 |
|---|---|---|
| <同一 Feature Ask> | <A>, <B> | P1 |
| <同一竞品对比> | <C>, <D> | 竞品威胁 |
| <同一技术报错> | <A>, <C> | 需产品介入 |

---

## 无实质内容的聊天

| 聊天 | 消息数 | 原因 |
|---|---|---|
| <name> | <n> | 全为打招呼/噪音 |
| <name> | 0 | 昨日无消息 |
```

---

## Categorization Decision Tree

```
Message received
    │
    ├── Length < 15 chars AND no product/customer name? → SKIP
    │
    ├── Error code / "报错" / stack trace / API failure? → [5] 技术问题
    │
    ├── "能不能" / "希望" / "支持" / "功能" / "什么时候有"? → [4] Feature Ask
    │
    ├── Competitor name mentioned (Runway/Kling/Sora...)? → [7] 竞品信号
    │
    ├── "换" / "别家" / "不满意" / deadline pressure? → [8] 风险信号
    │
    ├── Quota / usage / billing / "充值"? → [9] 用量配额
    │
    ├── "合同" / "续费" / "报价" / "采购" / "上线"? → [6] 商务进展
    │
    ├── New person / "新同事" / role change? → [10] 人员变动
    │
    ├── Customer has wrong understanding? → [11] 产品理解偏差
    │
    ├── Positive sentiment about product? → [2] 客户反馈（正面）
    │
    ├── Negative sentiment / complaint? → [3] 客户反馈（负面）
    │
    ├── Agreement / "就这样" / "定了"? → [12] 决策
    │
    ├── Question unanswered / issue unresolved? → [12] 待跟进
    │
    └── Other meaningful content? → [1] 重点内容
```

Note: A single message can belong to multiple dimensions (e.g., a complaint that's also a Feature Ask). Extract for all applicable dimensions.

---

## Wiki Write Decision Tree

```
Dimension → Local wiki action → Lark wiki (sa-wiki) action

[1] Key Points
    → Inline on customer page ## Recent interactions
    → (no Lark write needed unless cross-entity)

[2] Positive Feedback
    → Inline on customer page
    → (no Lark write; too granular)

[3] Negative Feedback
    → Inline on customer page
    → If repeating across 2+ customers: APPEND to existing feedback page in Lark wiki

[4] Feature Ask
    → CREATE feedback-<slug>.md in local wiki/concepts/
    → Lark wiki: CREATE feedback page OR APPEND requesters to existing one

[5] Technical Issue
    → If known error code: APPEND to existing error-code page
    → If new: CREATE error-code-<slug>.md
    → Lark wiki: CREATE/APPEND error-code page

[6] Business Progress
    → Inline on customer page (NO dollar amounts)
    → Lark wiki: APPEND TIMELINE (sanitised — no contract amounts)

[7] Competitive Signal
    → Inline on customer page
    → Lark wiki: if same competitor mentioned by 2+ customers → APPEND to relevant topic page

[8] Risk Signal
    → Flag on customer page in ## Open feedback / pain points
    → Lark wiki: APPEND TIMELINE with risk flag tag

[9] Usage / Quota
    → Inline on customer page
    → Lark wiki: if quota blocker → APPEND TIMELINE

[10] Personnel Change
    → CREATE / UPDATE person page in local wiki
    → Update customer page lark_chat / contacts if needed
    → (no Lark write unless significant org change)

[11] Misunderstanding
    → Inline note on customer page
    → If generalizable: CREATE concept page or APPEND to product page in Lark wiki

[12] Decisions & Pending
    → Inline on customer page (decisions past-tense, pending as open notes — no checkboxes)
    → (no Lark write unless decision involves a commitment from BytePlus side)
```

---

## Sensitivity Rules

Before writing to either wiki, verify content does NOT contain:
- AK / SK / tokens / passwords (32+ char alphanumeric strings)
- Customer PII (phone, ID card, email → `[redacted]`)
- Contract dollar amounts → replace with "price discussed"
- Individual performance evaluations
- L4-classified documents (full text)

Sensitive content stays in `raw/` only.
