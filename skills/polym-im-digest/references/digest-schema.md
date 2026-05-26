# Digest Schema — Priority-First IM Digest

This schema converts raw Lark IM messages into an SA-ready daily intelligence
report. It preserves the original 12 signal dimensions, but the rendered output
is priority-first rather than chat-first.

## Product Taxonomy

Apply product classification before prioritisation. See
[`product-context.md`](product-context.md) for aliases and ownership hints.

Use three separate fields instead of mixing platform, product, and modality:

| Field | Meaning | Examples |
|-|-|-|
| Product line | Commercial/platform owner bucket | ModelArk / MaaS, Public Cloud / Infra / Ops, Other |
| Offering / model | Concrete product/model/service | Seedance, Seedream, Seed2.0, Seed-SC, Doubao, DeepSeek, Ark API, Viking |
| Capability / modality | Workload or topic | Video generation, image generation, LoRA, copyright review, endpoint integration |

`AIGC Video / Image` is not a product line. It is a capability/modality label
for Seedance / Seedream workflows. ModelArk / MaaS items must not be buried
behind public-cloud or internal ops chatter.

## Priority Model

Assign exactly one priority to every actionable signal:

| Priority | Meaning | Examples |
|-|-|-|
| P0 | Immediate customer/business risk, production incident, compliance/legal red line, major escalation | production outage, compliance violation, customer public escalation, payment blocker with deadline today |
| P1 | High-impact issue or opportunity requiring owner follow-up within 24-48h | integration blocker, active POC blocker, high-value deal milestone, repeated unresolved customer complaint |
| P2 | Important but not urgent; should be tracked or turned into FAQ/doc/product backlog | roadmap ask, access policy clarification, nonblocking performance concern |
| P3 | Informational progress or low-risk update | launch notice, healthy delivery progress, FYI |

Every `P0` / `P1` item must include `owner`, `deadline`, `source channel`, and
`background`. If the source does not name an owner or deadline, write `TBD` and
include the item in `Owner / Deadline Gaps`.

## Analysis Dimensions

Extract along all 12 dimensions. Omit a dimension only if there is genuinely
nothing to extract. A message can contribute to multiple dimensions.

---

### 1. Key Points

General noteworthy information. **Always include** for chats with any meaningful content.
- What was the most important thing that happened yesterday in this chat?
- 1–3 bullets max; must-reads for any SA who missed the day.

---

### 2. Customer Feedback — Positive

Customer expressions of satisfaction, surprise, or appreciation.

Extraction signals: "效果不错"、"挺好的"、"比我想的好"、"满意"、"好用"、"准确"、"推荐"

Capture: what specifically impressed them, which product/feature.

---

### 3. Customer Feedback — Negative (Complaints)

Customer dissatisfaction, bugs, broken expectations.

Extraction signals: "有问题"、"报错了"、"效果差"、"用不了"、"比 X 差"、"不稳定"、"太慢"

Capture: what broke / disappointed, severity hint (blocking/annoying/minor).

---

### 4. Feature Asks

Explicit requests for features, capabilities, or behavioral changes.

Extraction signals: "能不能支持"、"希望有"、"什么时候有"、"能加一个"、"建议"

Capture: the ask verbatim or close paraphrase, who asked, why (if stated), which product.

---

### 5. Technical Issues & Errors

API errors, integration blockers, performance issues, configuration problems.

Extraction signals: error codes, stack traces, "API 返回"、"403"、"timeout"、"SDK"、"鉴权"

Capture: error code or description, context (what they were doing), whether it blocked them.

---

### 6. Business Progress

Contract discussions, pricing negotiations, renewal signals, deal stage changes, payment nodes, POC milestones.

Extraction signals: "合同"、"续费"、"报价"、"付款"、"采购"、"审批"、"上线"、"milestone"、"预算"

Capture: what stage, any amounts (redact specifics — use "price discussed"), timeline.

> ⚠️ Sensitivity: DO NOT write dollar amounts to wiki. Use "price discussed" or "contract topic raised."

---

### 7. Competitive Intelligence

Mentions of competitors, comparisons, switching discussions.

Watch for: Runway, Pika, Kling, Sora, MidJourney, Stable Diffusion, OpenAI, Google Veo, Hailuo, Wan, Jimeng, Dreamina, Luma, ElevenLabs, and any "competitor" / "别家" / "换一个"

Capture: which competitor, in what context (comparison, switching threat, partnership), sentiment.

---

### 8. Risk Signals (Churn / Risk)

Signs that the customer relationship is at risk.

Extraction signals:
- Switching intent: "考虑换"、"试试别家"、"别家可以做"
- Strong dissatisfaction: repeated complaints, escalation language
- Deadline pressure: "必须下周"、"领导催"、"已经 delay 很久了"
- Ghosting reversal: sudden message after long silence
- Budget cut signals: "预算削减"、"暂停"

**Always flag for SA attention even if mild.** Better false positive than miss.

---

### 9. Usage & Quota

Quota issues, usage spikes, billing questions, cost concerns.

Extraction signals: "quota 不够"、"超额"、"用量"、"账单"、"充值"、"token"、"限制"

Capture: what limit was hit, impact on customer (blocked / slowed), what they need.

---

### 10. Personnel & Org Changes

New contacts joining, decision-maker changes, team restructuring, contact going silent.

Extraction signals: new person @, "新同事"、"换了负责人"、"原来的 XX 离职了"、"加了个 CTO"

Capture: who joined/left, their role; update person page in wiki.

---

### 11. Product Misunderstandings / Clarifications Needed

Customer has an incorrect understanding of product capabilities, limitations, or roadmap.

Extraction signals:
- "我以为能..."（but actually can't）
- "你们说过..."（but that's not what was said）
- Asking for something that already exists
- Expecting a feature that's not on roadmap

Capture: what they misunderstood, what the correct understanding is, whether SA needs to follow up.

---

### 12. Decisions & Pending Items

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

## Deduplication and Canonical Issues

Do not let one issue appear as multiple independent highlights just because it
appears in multiple chats or sections.

Rules:

- Create one canonical issue for each `(customer/product/root cause)` tuple.
- Merge repeated bot alerts into one canonical root cause with count and time
  range.
- If the same item appears in Executive Summary and a product drill-down, the
  drill-down should add compact evidence only, not repeat the full narrative.
- Known duplicate-prone examples: OKX delivery status, Snapdeal stale alerts,
  ModelArk oncall clusters, Seedance performance notices.

## Coverage Checks

Before rendering, run these checks:

- `Executive Summary` exists and has 3-7 numbered takeaways.
- `Priority Queue` exists and includes every P0/P1 item.
- `Owner / Deadline Gaps` exists when any P0/P1 has `TBD` owner or deadline.
- ModelArk / MaaS items render before public-cloud and internal ops items.
- If raw messages contain `Seedance`, `Seedream`, `ModelArk`, `Ark`, `Doubao`,
  `xLLM`, `Viking`, `ArkClaw`, or `AgentKit`, at least one relevant item appears
  in the digest unless all matching messages are explicitly filtered as noise.
- Every priority item includes source channel/chat and evidence timestamp.

---

## Output Format Template

```markdown
# IM Digest · <YESTERDAY>

> Scanned <N> active conversations: <P> P2P threads and <G> group chats. Fetched <M> messages; <K> passed signal filter.  
> Focus order: ModelArk / MaaS -> Public Cloud / Infra / Ops -> Other.  
> Source: Lark IM · Skipped by local blacklist: <B>

---

## Executive Summary

### Top Takeaways

1. <priority> · <product line> · <offering/model> · **<customer/topic>**: <one-sentence implication + required action>.
2. ...

### Priority Queue

| Pri | Product line | Offering / model | Capability | Customer / chat | Issue / highlight | Channel & background | Owner | Deadline | Status / next step | Evidence |
|-|-|-|-|-|-|-|-|-|-|-|
| P0 | ModelArk / MaaS | Seedance | Video generation / safety | <customer/chat> | <canonical issue> | `<channel/chat>`; <why this matters> | <owner or TBD> | <deadline or TBD> | <next action> | <sender HH:MM> |

### Owner / Deadline Gaps

| Pri | Customer / chat | Gap | Why it matters | Suggested owner |
|-|-|-|-|-|
| P1 | <customer/chat> | Owner TBD / deadline TBD | <risk> | <suggested owner> |

### Highlights

- <priority> **[<source channel>] <customer/topic>**: <concise highlight with owner/deadline if available>.

## Product Drill-Down

### ModelArk / MaaS

| Pri | Offering / model | Capability | Customer / chat | Type | Summary | Owner | Deadline | Status |
|-|-|-|-|-|-|-|-|-|
| P1 | Seedance | Video generation / safety | <customer/chat> | Technical Issue | <summary> | <owner> | <deadline> | <status> |

**Details**

- <canonical issue>: <compact supporting detail, not a duplicate of the top narrative>.

### Public Cloud / Infra / Ops

<same table + details>

### Other / Low Signal

Only include if needed; keep compact.

---

## Cross-Chat Patterns

> Only generate when the same pattern appears in 2+ chats.

| Pattern | Product line | Offering / model | Customers involved | Priority | Recommended handling |
|-|-|-|-|-|-|
| <pattern> | ModelArk / MaaS | Seedance / Seedream | <A>, <B> | P1 | <action> |

## Risks

- <priority> **<risk>**: <why it matters, likely consequence, owner/deadline>.

## Business / Pipeline Updates

| Customer | Stage | Current status | BytePlus owner | Health |
|-|-|-|-|-|
| <customer> | <POC/contract/access/etc.> | <status> | <owner> | 🟢/🟡/🔴 |

---

## Chat Appendix

### <Customer Name / Chat Name>

**Message count**: <n> · **Active period**: <HH:MM-HH:MM> · **chat_id**: <oc_xxx> · **Product line**: <line> · **Offering/model**: <offering>

| Time | Sender | Signal | Pri | Product line | Offering / model | Capability | Notes |
|-|-|-|-|-|-|-|-|
| <HH:MM> | <sender> | <dimension/type> | <P*> | ModelArk / MaaS | Seedance | Video generation | <short evidence> |

## Chats with No Substantive Content

| Chat | Message count | Reason |
|-|-|-|
| <name> | <n> | All greetings / noise |
```

---

## Categorization Decision Tree

```
Message received
    │
    ├── Length < 15 chars AND no product/customer name? → SKIP
    │
    ├── Error code / "报错" / stack trace / API failure? → [5] Technical Issues
    │
    ├── "能不能" / "希望" / "支持" / "功能" / "什么时候有"? → [4] Feature Ask
    │
    ├── Competitor name mentioned (Runway/Kling/Sora...)? → [7] Competitive Intelligence
    │
    ├── "换" / "别家" / "不满意" / deadline pressure? → [8] Risk Signals
    │
    ├── Quota / usage / billing / "充值"? → [9] Usage & Quota
    │
    ├── "合同" / "续费" / "报价" / "采购" / "上线"? → [6] Business Progress
    │
    ├── New person / "新同事" / role change? → [10] Personnel Changes
    │
    ├── Customer has wrong understanding? → [11] Product Misunderstandings
    │
    ├── Positive sentiment about product? → [2] Customer Feedback (Positive)
    │
    ├── Negative sentiment / complaint? → [3] Customer Feedback (Negative)
    │
    ├── Agreement / "就这样" / "定了"? → [12] Decisions
    │
    ├── Question unanswered / issue unresolved? → [12] Pending Items
    │
    └── Other meaningful content? → [1] Key Points
```

Note: A single message can belong to multiple dimensions. Extract for all applicable dimensions.

---

## Wiki Write Decision Tree

```
Dimension → Local wiki action → Lark wiki (polym-sa-wiki) action

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
    → Lark wiki: APPEND TIMELINE (sanitised)

[7] Competitive Signal
    → Inline on customer page
    → Lark wiki: if same competitor in 2+ customers → APPEND to relevant topic page

[8] Risk Signal
    → Flag on customer page in ## Open feedback / pain points
    → Lark wiki: APPEND TIMELINE with risk flag tag

[9] Usage / Quota
    → Inline on customer page
    → Lark wiki: if quota blocker → APPEND TIMELINE

[10] Personnel Change
    → CREATE / UPDATE person page in local wiki
    → Update customer page lark_chat / contacts if needed

[11] Misunderstanding
    → Inline note on customer page
    → If generalizable: CREATE concept page or APPEND to product page in Lark wiki

[12] Decisions & Pending
    → Inline on customer page (decisions past-tense, pending as open notes — no checkboxes)
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
