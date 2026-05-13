---
name: meeting-summary
version: 0.1.0
description: "Compile all meetings (Lark VC + Minutes) over a time period, extract customer insights and key conclusions, and automatically save to the knowledge base. Default range: yesterday 00:00 to now. Trigger phrases: '整理最近的会议', 'meeting summary', '帮我总结一下昨天的会', '会议纪要整理'."
metadata:
  requires:
    bins: ["lark-cli"]
---

# meeting-summary — Meeting Content Compilation

Compile all Lark meetings over a time period into structured knowledge and automatically save to the knowledge base.

## Trigger Scenarios

- "Organize recent meetings"
- "Help me summarize yesterday's meetings"
- "meeting summary"
- "Meeting notes compilation"
- "Compile meetings from [time range]"
- "整理最近的会议"
- "帮我总结一下昨天的会"
- "会议纪要整理"

## Dependencies

- `lark-cli` (vc module + minutes module)
- Local wiki (path auto-resolved, see Phase 0)
- Lark wiki writes delegated to the **sa-wiki skill**

---

## Complete Execution Flow

### Phase 0 — Preparation

**0.1 Determine Time Range**

Default: yesterday 00:00 to now.

```bash
# macOS
YESTERDAY=$(date -v-1d +%Y-%m-%d)
START_TIME="${YESTERDAY}T00:00:00+08:00"
NOW=$(date -u +"%Y-%m-%dT%H:%M:%S+08:00")

# Linux
YESTERDAY=$(date -d yesterday +%Y-%m-%d)
```

If the user specifies a time range ("last week's meetings", "May 10th to 12th"), parse accordingly.

**0.2 Local Wiki Path Resolution (per `core/local-wiki-ux.md` standard)**

1. Check `LOCAL_WIKI_ROOT` environment variable
2. Look up `local-wiki-root` in Claude's memory system
3. Auto-detect: `~/sa-wiki`, `~/wiki`, `~/LLM-Wiki`
4. None found → ask once: "No local wiki found yet. Would you like to create one? [Y/n]"
   - Y: "Where should it be saved? (press Enter for default ~/sa-wiki)" → call `local-wiki-init` → save to memory
   - N: Skip local write for this session

---

### Phase 1 — Discover Meetings

**1.1 Query Lark VC Meeting History**

```bash
lark-cli vc +meetings-list \
  --start-time "$START_TIME" \
  --end-time "$NOW" \
  --format json --as user
```

**1.2 Query Lark Minutes**

```bash
lark-cli minutes +list \
  --start-time "$START_TIME" \
  --end-time "$NOW" \
  --format json --as user
```

Merge both sources, deduplicate (same meeting may appear in both VC and Minutes), sort ascending by start time.

Display the meeting list (title, time, duration). Mark meetings not attended as `[not attended]` but still process them (if Minutes are available).

---

### Phase 2 — Fetch Content for Each Meeting

**For each meeting**, retrieve content by priority:

**Priority: Lark Minutes AI outputs (most structured)**

```bash
# Get meeting summary
lark-cli minutes +get-summary --token <minute_token> --as user

# Get chapters (timestamped segments)
lark-cli minutes +get-chapters --token <minute_token> --as user

# Get action items
lark-cli minutes +get-todos --token <minute_token> --as user
```

**Fallback: Lark Minutes verbatim transcript**

```bash
lark-cli minutes +get-transcript --token <minute_token> --as user
```

**Last resort: VC meeting details**

```bash
lark-cli vc +meeting-detail --meeting-id <meeting_id> --as user
```

For meetings with only a VC record and no Minutes: record only basic info (attendees, duration), mark as `[no recording/notes]`.

---

### Phase 3 — Analysis and Extraction

For each meeting, extract along the following dimensions (skip if no content):

| # | Dimension | Description |
|---|---|---|
| 1 | **Meeting Purpose** | What this meeting was about, in one sentence |
| 2 | **Key Conclusions** | Consensus reached and decisions made, stated in past tense |
| 3 | **Customer Feedback** | Positive/negative, specific product/feature |
| 4 | **Feature Asks** | Explicitly requested requirements from the customer |
| 5 | **Technical Issues** | Errors, integration pain points, API issues |
| 6 | **Business Progress** | Contract, renewal, POC milestones (monetary amounts not stored in wiki) |
| 7 | **Competitor Signals** | Mentioned competitors and comparative comments |
| 8 | **⚠️ Risk Signals** | Churn risk, strong dissatisfaction, deadline pressure |
| 9 | **Follow-ups** | Items mentioned but unresolved, or commitments made but not yet delivered |
| 10 | **Attendees** | Key contacts on the customer side (name, role) |

**Cross-meeting aggregation** (after all meetings are processed):
- Multiple meetings for the same customer → merge into one customer summary
- Same issue appearing in multiple meetings → cross-meeting insight

---

### Phase 4 — Output Summary

```markdown
# Meeting Summary — <YESTERDAY> → <NOW>

Total <N> meetings · <M> with Minutes

---

## <Customer Name> · <Meeting Title> · <HH:MM> (<duration>min)

### Key Conclusions
- <past-tense decision>

### Customer Feedback
- <feedback>

### Feature Asks
- "<ask>" — <who>, product: <product>

### ⚠️ Risk Signals
- <signal>

### Follow-ups
- <item>

---

## [No Minutes] <Meeting Title> · <Time>
Attendees: <N> · Duration: <M> min · No meeting notes

---

## Cross-Meeting Insights
- <insight> (across <N> meetings)
```

**After output is complete, write immediately without asking the user.**

---

### Phase 5 — Write to Local Wiki (Silent)

**Only execute silently when LOCAL_WIKI_ROOT is valid.**

For each meeting with content:

1. **Create source page** `wiki/sources/meeting-<slug>-<DATE>.md`
2. **Update customer page** `wiki/entities/customers/<slug>.md`:
   - Append a line + link under `## Recent interactions`
   - New Feature ask → add link under `## Open feedback`
   - Business progress → update `status` frontmatter (if changed)
   - Risk signal → annotate under `## Open feedback / pain points`
3. If new attendees → create/update `wiki/entities/people/<slug>.md`
4. Update `wiki/index.md` + append to `wiki/log.md`

---

### Phase 6 — Write to Lark Wiki

**Execute automatically using sa-wiki skill §5 WRITE workflow.**

- Each customer with content → APPEND TIMELINE
- Feature Asks → CREATE/APPEND feedback page
- Technical issues → CREATE/APPEND error-code page
- Risk signals → APPEND TIMELINE (with risk tag)
- Execute desensitization before writing (`META_DESENSITIZATION`, managed by sa-wiki)

---

### Phase 7 — Closing Report

```
✅  Meeting compilation complete (<YESTERDAY> → now)

<N> meetings · <M> with Minutes · <K> customers updated

Summary:
  Key conclusions: <N>
  Feature asks: <N>
  Competitor signals: <N>
  ⚠️ Risk signals: <N> (suggested follow-up: <customer name>)

Saved <K> entries to knowledge base (<proposal_ids>)
```

---

## Safety Rules

- Do not write contract amounts; use "price discussed"
- Desensitization is handled by sa-wiki
- Only write meetings that you attended or have Minutes access to
- Do not use `docs +update` to directly modify wiki pages

## Reference Documents

- [`core/local-wiki-ux.md`](../../core/local-wiki-ux.md)
- [`references/meeting-fetch.md`](references/meeting-fetch.md)
