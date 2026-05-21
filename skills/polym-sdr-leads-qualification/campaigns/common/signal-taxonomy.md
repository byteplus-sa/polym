## LinkedIn Signal Taxonomy

Signal types ranked by intent strength (highest to lowest):

| Interaction Type | Signal Strength | Notes |
|-----------------|-----------------|-------|
| Posted on LinkedIn | high | They created content — active engagement, top of mind |
| Commented on LinkedIn | medium | They engaged in depth — shows real interest |
| Liked / Reacted on LinkedIn | medium-low | Passive signal, but valid if ICP + persona match |
| Job posting (hiring AI/video roles) | medium–high | Company investing in this workflow |
| Company news / funding | medium | Context-dependent — look for video/AI angle |
| Intent data (browsing AI/video tools) | medium–high | Actively researching solutions |
| Event attendance (AI/video conference) | medium | In the ecosystem |

## Signal Strength Classification

| Strength | When to apply | Example |
|----------|---------------|---------|
| **high** | Explicit purchase intent, direct pain stated, active evaluation of video/AI tools, OR posted about video/AI production challenges | "Actively evaluating AI video tools", "our pipeline is too slow", hiring a Head of AI Content |
| **medium** | Indirect interest, commented on relevant content, company-level signal with video/AI angle | Commented on an AI video post, company launched video initiative, hiring video editors |
| **medium-low** | Liked relevant content from right ICP/persona, adjacent workflow, company signal with weak video angle | Liked a post about AI video tools, general creative industry news |
| **low** | Noise — wrong ICP, wrong persona, and engagement has no video/AI/creative relevance | Finance person liked a generic AI article, junior role liked unrelated content |

Assign "low" signal_strength only when BOTH are true:
- Wrong ICP segment (company has no plausible use case)
- Wrong persona (junior role or irrelevant function)

A right-segment or right-persona like should always be medium-low, never low.

Signal strength values: "high" | "medium" | "medium-low" | "low"

## Signal → Intent → Pain → Use Case

```
Signal (what Trigify captured)
  ↓
Intent (what the person/company is doing or thinking)
  ↓
Pain (what problem they likely have)
  ↓
Use Case (how the product addresses it)
```

### Example — High Signal (Posted)
Signal: "Creative Director at a film production company posted: 'Our team is spending 75% of time on manual edits. Looking for AI solutions to scale output.'"
- Interaction: Posted → HIGH signal
- Intent: Actively seeking AI video solution
- Pain: Manual editing at scale is the bottleneck
- Use Case: AI video generation to replace manual editing steps

### Example — Medium-Low Signal (Liked) — Right ICP
Signal: "Founder of a short drama production company liked a post about AI video capabilities."
- Interaction: Liked → MEDIUM-LOW (not low — founder of short drama = strong ICP)
- Intent: Aware of the solution space, curious
- Pain: Inferred — short drama production demands high-volume short video output
- Use Case: Short-form AI video generation at scale

### Example — Low Signal (Liked) — Wrong ICP
Signal: "HR Manager at a logistics company liked a post about AI technology trends."
- Interaction: Liked → LOW (wrong ICP + wrong persona + no video relevance)
- Intent: General AI curiosity
- Pain: None identified
- Use Case: None — hard disqualify candidate

## Company Momentum Signals

Look for these in the signal text or Trigify note — they indicate a company in motion. Flag in observed_evidence when present.

| Signal | Strength Boost | Why it matters |
|--------|----------------|----------------|
| Hiring for AI, video, or creative roles | +1 level | Company actively investing in this workflow |
| New CEO, CMO, or Head of Production recently appointed | +1 level | New leaders make change — high receptivity window |
| Recent funding round | Neutral (context) | Budget available, but only relevant if ICP matches |
| Strategic product launch / expansion | Neutral (context) | Growth mode = content production demand increases |
| Agency pitching / competing for new clients | +1 level | Under commercial pressure to deliver faster |

## New Executive Signal (High Priority)

Executives newly appointed (< 12 months) are prime outreach targets — they are under pressure to deliver results and actively seeking change.

If the signal or profile shows someone recently started a senior role:
- Flag it as "New executive — recently appointed" in observed_evidence
- Boost buyer_fit scoring by 3–5 points even for Director-level titles
