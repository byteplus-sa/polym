# Feishu Doc Visual Style

The digest should be readable as an operational dashboard, not just a plain
markdown dump. Use the richest format supported by the installed `lark-cli`.

## Renderer Selection

1. Render XML by default and create the Feishu doc with
   `--content @./file.visual.xml --doc-format xml`.
2. Keep a Markdown copy for terminal review and as a fallback if XML creation
   fails.
3. Do not use Markdown pipe tables as the primary Feishu output; they can render
   as literal text and make the doc hard to scan.

## Visual Blocks for XML Renderer

Use the Lark Doc XML subset:

- `<title>` for the document title.
- `<callout>` for Executive Summary, P0/P1 warnings, and owner/deadline gaps.
- `<grid>` and `<column>` for compact metric cards at the top.
- `<table>` with colored header cells for Priority Queue, Pipeline, and
  Product Drill-Down.
- `<checkbox>` for high-priority next steps when there is a clear owner.
- `<bookmark>` for linked Feishu docs, customer docs, or referenced resources.
- `<hr/>` between major sections.
- `<span text-color>` and `<span background-color>` for priority badges.

## Canonical Layout

Use this section order for the Feishu XML doc:

1. Title: `IM Digest · <date>`.
2. Four metric cards in a `<grid>`: Active chats, P0/P1, ModelArk / MaaS items,
   Owner gaps.
3. Executive Summary in a blue callout with 3-7 numbered takeaways.
4. Priority Queue as the first real table.
5. Owner / Deadline Gaps in a yellow callout.
6. Highlights.
7. Action Items as checkboxes.
8. Product Drill-Down with sections for `ModelArk / MaaS`,
   `Public Cloud / Infra / Ops`, and `Other / Low Signal`.
9. Cross-Chat Patterns.
10. Risks in a red callout when there are active risks.
11. Business / Pipeline Updates.
12. Chat Appendix with one compact evidence table per substantive chat and a
    final table for chats with no substantive content.

This layout is the default. Do not replace it with a shorter summary layout.

## Content Parity

Visual formatting must not summarize away content. Treat the Markdown digest as
the content ledger and the XML digest as the rendered view.

Before creating or updating the Feishu doc, verify the XML includes:

- Every top-level section from the Markdown digest.
- Every Priority Queue row.
- Every Product Drill-Down row, including P2/P3 and low-signal rows.
- The full Risks and Business / Pipeline Updates sections.
- Chat Appendix entries for every chat that appears in the Markdown appendix,
  including "Chats With No Substantive Content".

If a compact dashboard is added at the top, it is additive only. It cannot
replace the detailed sections below it.

## Color System

Use consistent priority colors:

| Priority | Color | XML hint |
|-|-|-|
| P0 | red | `background-color="light-red"` / `text-color="red"` |
| P1 | orange | `background-color="light-orange"` / `text-color="orange"` |
| P2 | yellow | `background-color="light-yellow"` / `text-color="orange"` |
| P3 | green | `background-color="light-green"` / `text-color="green"` |
| Info | gray | `background-color="light-gray"` |

## Top Layout

Recommended XML structure:

```xml
<title>IM Digest · 2026-05-26</title>

<grid>
  <column width-ratio="0.25"><callout emoji="📌" background-color="light-blue"><p><b>Active chats</b><br/>35</p></callout></column>
  <column width-ratio="0.25"><callout emoji="🔥" background-color="light-red"><p><b>P0/P1</b><br/>7</p></callout></column>
  <column width-ratio="0.25"><callout emoji="🧭" background-color="light-purple"><p><b>MaaS items</b><br/>5</p></callout></column>
  <column width-ratio="0.25"><callout emoji="⚠️" background-color="light-yellow"><p><b>Owner gaps</b><br/>3</p></callout></column>
</grid>

<callout emoji="🎯" background-color="light-blue" border-color="blue">
  <h2>Executive Summary</h2>
  <ol>
    <li seq="auto">P1 · ModelArk / MaaS · Seedance · ...</li>
  </ol>
</callout>
```

## Priority Queue Table

The Priority Queue should be the most visually scannable section:

```xml
<h2>Priority Queue</h2>
<table>
  <thead>
    <tr>
      <th background-color="light-gray">Pri</th>
      <th background-color="light-gray">Product line</th>
      <th background-color="light-gray">Offering / model</th>
      <th background-color="light-gray">Capability</th>
      <th background-color="light-gray">Customer / Chat</th>
      <th background-color="light-gray">Issue / Highlight</th>
      <th background-color="light-gray">Owner</th>
      <th background-color="light-gray">Deadline</th>
      <th background-color="light-gray">Next Step</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td background-color="light-orange"><b>P1</b></td>
      <td>ModelArk / MaaS</td>
      <td>Seedance</td>
      <td>Video generation / safety</td>
      <td>Example customer</td>
      <td>Canonical issue summary</td>
      <td>TBD</td>
      <td>TBD</td>
      <td>Assign owner and publish response</td>
    </tr>
  </tbody>
</table>
```

## Markdown Fallback

When XML is unavailable:

- Keep the same section order.
- Use emoji priority badges: `🔴 P0`, `🟠 P1`, `🟡 P2`, `🟢 P3`.
- Use compact tables instead of long bullets.
- Use blockquotes for Executive Summary and urgent warnings.
- Keep Chat Appendix compact and evidence-oriented.

## Writing Rules

- Prefer short, dense table cells over paragraph-heavy sections.
- Put actions before evidence.
- Never repeat the same issue narrative in multiple sections.
- Keep raw message excerpts out of the main body unless they are essential
  evidence for a P0/P1.
