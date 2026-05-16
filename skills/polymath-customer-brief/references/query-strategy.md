# Query Strategy & Result Merging

## Speed Tiers

| Mode | Queries | Typical latency | When to use |
|---|---|---|---|
| `--quick` | ① polymath-sa-wiki + ② local wiki | ~5s | On the run, already know the customer well |
| default | ① + ② + ③ IM search | ~10s | Normal pre-meeting prep |
| `--full` | ① + ② + ③ + ④ C360 | ~20s | First meeting, renewal prep, risk situation |

## Deduplication Rules

When the same event appears in multiple sources, keep one entry.

**Priority (most authoritative → least):**
1. polymath-sa-wiki TIMELINE (curated, already processed)
2. Local wiki sources (processed by a previous digest run)
3. Live IM messages (raw, but freshest)
4. C360 (numbers only, no narrative)

**Conflict handling:**
- Wiki says status = `poc`, IM says "我们已经上线了" → use IM, tag `[wiki 可能过时]`
- Wiki has an open feedback, IM mentions "那个问题解决了" → keep feedback but note it may be resolved

## Commitment Detection

Look for our-side commitments in:

1. polymath-sa-wiki TIMELINE entries with type = `decision` or phrases like:
   - "王文杰 to follow up"
   - "BytePlus 提供"
   - "我们下周..."
   - "SA 承诺"
   - "需要 SA 确认"

2. Local wiki interaction pages: `## Outcomes` section

3. Recent IM: messages from internal BytePlus senders containing:
   - "我来跟进"
   - "我去问一下"
   - "下周给你回复"
   - "我帮你确认"

**Overdue threshold:** commitment date + 7 days without a follow-up entry in TIMELINE.

## Risk Signal Keywords

When scanning IM messages for risk signals, look for:

**High risk (always surface):**
- "考虑换" / "试试别家" / "其他家可以做"
- "非常不满意" / "严重影响" / "已经影响到业务"
- "合同不续了" / "暂停合作" / "先暂停"

**Medium risk (surface if recent):**
- Competitor name in same message as "比较" / "更好" / "更便宜"
- Consecutive days without response from customer
- Escalation language: "老板" / "投诉" / "升级"

**Low risk (surface only if --full):**
- General dissatisfaction without explicit switching intent
- Budget-related questions without urgency

## Unanswered Question Detection

A question is "unanswered" if:
1. It ends with `？` or contains "能不能" / "是否" / "什么时候" / "how"
2. It was sent by a customer-side participant
3. No subsequent message from an internal (BytePlus) participant directly addresses it
4. It's older than 3 days

## Customer Slug Resolution

To map `CUSTOMER` name to local wiki slug:
1. Try exact match: lowercase + replace spaces with `-`
2. Try removing legal suffix: "Corp" / "Inc" / "Ltd" / "有限公司"
3. Try checking `aliases` frontmatter in customer files
4. Try partial match: any customer file whose `aliases` contains the search term

Example: "Acme Corporation" → try `acme-corporation` → `acme` → check aliases

## C360 Chrome Check

Before triggering query ④:
```
result = mcp__Claude_in_Chrome__list_connected_browsers()
if not result or len(result) == 0:
    # Skip C360 silently in default mode
    # In --full mode: note "C360 unavailable (Chrome extension not connected)"
    skip_c360 = True
```

Do NOT guide through installation in polymath-customer-brief (that's polymath-dashboard-watch's job).
Just note it's unavailable and offer to run `polymath-dashboard-watch <CUSTOMER>` separately.

## Timeout Handling

Set a 25-second overall timeout.

If a query agent doesn't return in time:
- ①: critical — wait up to 25s, can't generate brief without wiki
- ②: skip gracefully (note "local wiki unavailable")
- ③: skip gracefully (note "live IM search skipped")
- ④: always skip after 20s

Final brief can be generated with partial data — always note which sources contributed.
