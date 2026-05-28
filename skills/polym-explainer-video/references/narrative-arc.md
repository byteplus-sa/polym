# Narrative arc — the storyboard is a story, not a screen catalogue

This is the most important reference doc in the skill. **Read it before drafting any storyboard.**

The patterns here are distilled from a real production-grade storyline that worked (the Syncore reference, captured at `~/Downloads/STORYLINE.md` if available on the host). They are NOT theoretical — they were field-tested and revised against actual viewer feedback.

---

## The mistake to avoid

Pure-broll product demos fail when the storyboard is structured as "here are 4 UI screens of the product, shown one after another, with a title card at each end." That's a screen catalogue. It tells the viewer what the product LOOKS LIKE, not what it DOES or WHY THEY SHOULD CARE.

Sign of this failure mode: the user watches the video and says "I don't get what it does." If your storyboard has 3+ device-mockup segments with no narrative thread tying them, you're making a screen catalogue. The auditor flags this as `severe`.

---

## The 8 patterns of a real storyline

### Pattern 1 — Canon (preserved entities)

Pick **3-5 specific entities** that get referenced by exact name across every frame. The viewer's brain locks onto specifics; abstractions slip away.

For the Syncore reference:
- The meeting: **Vertex Labs sync**
- The other party: **David Chen (Vertex Labs · david@vertexlabs.co)**
- The captured promise: *"I'll send you the rollout setup guide by Thursday."*
- The attached doc: **Notion — Vertex onboarding · rollout SOP**
- The other Today promises: Maya Singh / Acme, Tom Riley / Northwind, Jen Park / Helix

Notice: these are not categories ("a colleague"), they're proper nouns ("David Chen"). Not "a meeting", "Vertex Labs sync". Not "a commitment", the exact quoted sentence.

Generalizable rule: **draft the canon BEFORE drafting any frames**. The canon lives at the top level of `storyboard.json` as the `canon` field. Every frame must reference at least one canon entity by exact name.

### Pattern 2 — Echo (visual rhyme)

Pick **one specific artifact from the canon that recurs across 2+ frames at different moments**, in the same typography, holding the same visual weight. This is what makes the story feel intentional, not coincidental.

Syncore example: the quoted commitment *"I'll send you the rollout setup guide by Thursday."* appears in:
- **Frame 3** (the meeting transcript — accent-tinted)
- **Frame 6** (Claude's "You committed" field — italic Instrument Serif)
- **Frame 7** (the email body, implicitly)

Same sentence, same italic typography, **three frames apart**. The storyline's author calls this "the demo's central beat." The viewer doesn't consciously notice the echo, but they feel the loop closing.

Generalizable rule: **declare an `echo` array at the top level** listing the artifact + the frames it recurs in. The auditor checks that at least one echo spans 2+ frames.

### Pattern 3 — Cast (named protagonist + supporting cast)

Replace abstract "the user" with a **named protagonist with a role and situation**. Add a small supporting cast (1-3 people) that gets used across frames.

Syncore cast:
- Erica — protagonist, the meeting attendee who's making the promise
- David Chen — Vertex Labs PM, the other party
- Sam, Priya — call participants (mentioned in frame 2)

The cast lives at top level as the `cast` field. Each member has: name, role, affiliation, and (optionally) a 1-line motivation.

**For products without human personas** (a CLI, a daemon): the protagonist is the user-in-a-situation ("the on-call SRE at 3am"), the "other party" might be a system, a colleague, or oneself-in-the-future. Specificity still applies.

### Pattern 4 — Frame-name keyword

Give each frame a **short UPPERCASE keyword** that captures its essence in one word. Makes the storyboard scannable, helps the model and the user reason about the structure.

Syncore frames: `SUMMON / ALONGSIDE / DETECT / FILE / LATER / HAND OFF / KEPT / END`

Bad alternatives: `Frame 1`, `Today view`, `Device mockup with Today UI`. The keyword is a verb or a noun-as-state, never a description of what's on screen.

The keyword goes into `segment.frame_name` and shows up in the storyboard.md table for the approval gate.

### Pattern 5 — Per-frame narration cue (or explicit silent)

Every frame must declare either:
- A **narration cue** with a numbered ID + exact spoken line (e.g., `"03 · DETECT — Spots commitments as you make them. No tagging required."`)
- An **explicit `silent: true`** with a one-line reason (e.g., `"silent — the breather is the point"`)

There is no "narration TBD" or "narration optional". If you don't know what's said, you don't have a frame; you have a placeholder.

For pure-broll mode (no VO), the "narration" is still the implied voice the viewer reads in their head as the typography hits — it's the text-on-screen, not spoken audio. Declare it anyway, so the storyboard tells you what story the visuals are telling.

### Pattern 6 — Breather beat (optional sixth beat)

Insert one almost-empty silent frame between Magic and Promise. ~1.5-3s. No copy, no narration, just a temporal gap that lets the previous beat land before the closer arrives.

Syncore frame 5 (`— LATER —`): cream stage, hairline clock, "Thursday morning" in serif italic, mono caps `LATER`. Total ~2s. The breather is what makes the email-write-out in frame 7 feel earned — viewer registers that time has passed between the promise and the action.

Generalizable rule: any storyline over ~30s benefits from a breather. Declare it as a segment with `type: "breather"`, `silent: true`, and a 1-line metaphor for the time/space being marked.

### Pattern 7 — Click-driven transitions (action causes next scene)

The strongest storytelling pattern: each major scene transition is **caused by a visible cursor action in the previous scene**, not by a music cut or fade. The viewer's hand drives the story.

Syncore has 4 clicks, each triggers the next scene:

| Click | Time | Button | Triggers |
|---|---|---|---|
| 1 | 2.55s | `Start meeting notes` | → meeting begins (F2) |
| 2 | 17.35s | `Draft` on the new card | → Claude opens (F6) |
| 3 | 30.30s | `Send` on the prompt card | → Claude drafts (F7) |
| 4 | 38.55s | `Send` on the email card | → promise kept (F8) |

Each click gets a click-ripple ring + cursor scale-punch + audio click SFX. The visual ripple sells "this action mattered."

Generalizable rule: in pure-broll mode, declare `click_triggers_next: true` on the segment that ends with a click, and the next segment's `start` must align (within 0.2s) with the click time. The auditor checks the alignment.

**This pattern only works for UI products.** Skip for abstract / brand-only videos.

### Pattern 8 — Storyline-as-handoff document

The storyboard isn't a creative wishlist; it's a **production handoff document**. The Syncore STORYLINE.md ends with:

- **The canon** (preserved across every frame)
- **What drives the narrative forward** (the 4 click chain table)
- **What's locked** (final video file path, source compositions, audio handoff doc)

These sections turn the storyline into something the next person (or the model, in a future session) can use to continue production without losing context.

Generalizable rule: storyboard.md generated for the approval gate must include these 3 trailing sections, not just the timeline table. The user reads them as part of approval.

---

## The 5-beat arc, refined

The basic 5-beat structure (hook → tension → reveal → magic → promise) still applies. With the 8 patterns above, here's how to fill each beat:

| Beat | What it does | Required patterns | Typical length (30-45s video) |
|---|---|---|---|
| **1. Hook** | Open with the world-as-it-is, or the protagonist's situation | frame_name, narration | 3-5s |
| **2. Tension** | Show the friction the product addresses | frame_name, narration, canon-entity reference | 5-8s |
| **3. Reveal** | Introduce the product. First sight of the UI. | frame_name, narration, canon-entity, click_triggers_next | 6-10s |
| **4. Magic** | The "ah, that's it" moment. Echo lands here. | frame_name, narration, echo, click_triggers_next | 10-18s |
| **5. (optional) Breather** | Silent gap | frame_name, silent:true | 1.5-3s |
| **6. Promise** | The world-as-it-could-be, plus brand + CTA | frame_name, narration, canon-entity (final reference) | 5-8s |

---

## Drafting checklist (do these IN ORDER, BEFORE writing any segment)

1. **Cast** — who's the named protagonist? Supporting cast (1-3)?
2. **Canon** — list 3-5 specific entities (meeting/person/quote/doc/etc) with exact names
3. **Echo** — which 1 canon entity recurs in 2+ frames as the central rhyme?
4. **5 narrative answers** (still required from prior version):
   - protagonist
   - problem
   - moment_of_magic
   - memorable_line
   - cta
5. **Frame-name keywords** — 1 word per planned segment
6. **Narration cues** — exact line per frame OR explicit silent
7. **Click chain** (UI products only) — list the clicks that trigger transitions
8. **Now draft the segments** using the above as the spec

If you can't fill 1-7 confidently, STOP and ask the user clarifying questions. The screen catalogue mistake (sequence of UI screens with no narrative thread) is the #1 reason finished videos don't communicate.

---

## Anti-patterns the auditor flags

| Pattern | Severity | Why it blocks |
|---|---|---|
| `narrative` fields missing or contain "REPLACE:" placeholders | severe | story not authored yet |
| `arc_map` missing any of hook/tension/reveal/magic/promise | severe | incomplete structure |
| `magic` beat shorter than `reveal` × 0.7 | severe | reveal is consuming the magic's screen time |
| 3+ device-mockup segments without `arc_map` | severe | screen catalogue |
| `canon` field missing or has fewer than 3 entries | severe | story too abstract |
| `echo` empty or only appears in 1 frame | warning | no visual rhyme |
| `cast.protagonist` is "user" / "viewer" / "developer" without specificity | warning | abstract persona |
| Any segment without `narration` or explicit `silent: true` | warning | undeclared voice |
| `click_triggers_next` set but next segment's `start` mismatched by >0.2s | warning | broken click chain |
| Any frame lacks `frame_name` | warning | unscannable storyboard |

Severities marked `severe` block the render. `warning` show in the approval gate but don't auto-block.

---

## Style preset alignment

| Preset | How the 8 patterns usually manifest |
|---|---|
| `openai-clean` | Canon = specific commands/files; Cast = developer protagonist; Echo = a specific output or filename; Clicks = terminal-driven |
| `anthropic-warm` | Canon = a specific person + meeting + quote (the Syncore pattern); Cast = a named professional; Echo = a quoted sentence in serif italic |
| `linear-minimal` | Canon = specific tickets/metrics; Echo = a metric that changes; Clicks = keyboard-shortcut driven |
| `apple-keynote` | Canon = the single hero product + a single user moment; Echo = a hero shot recurring; minimal narration |
| `brand-bold` | Canon = brand vocabulary repeated 3x; Echo = the same caps-mono word as a percussive beat |

---

## Concrete example — Syncore done right (the storyline from STORYLINE.md)

### Cast
- **Erica** — protagonist (the meeting attendee)
- **David Chen** — Vertex Labs PM, the other party
- Sam, Priya — call participants

### Canon
- Meeting: **Vertex Labs sync**
- Other party: **David Chen (Vertex Labs · david@vertexlabs.co)**
- Captured promise: *"I'll send you the rollout setup guide by Thursday."*
- Attached doc: **Notion — Vertex onboarding · rollout SOP**
- Background promises: Maya/Acme, Tom/Northwind, Jen/Helix

### Echo
The quoted commitment appears in frame 3 (transcript, accent-tinted) → frame 6 (Claude prompt's "You committed" field, italic Instrument Serif) → frame 7 (email body, implicitly). Same sentence, same italic typography, three frames apart.

### 8 frames (frame_name · time · narration cue)

| # | Time | Frame | Narration |
|---|---|---|---|
| 1 | 0.00 – 4.50 | **SUMMON** | "One keystroke, anywhere on your Mac. Syncore lives in the menu bar." |
| 2 | 4.10 – 7.60 | **ALONGSIDE** | "Listens during meetings — without taking over." |
| 3 | 7.45 – 13.45 | **DETECT** | "Spots commitments as you make them. No tagging required." |
| 4 | 12.95 – 19.45 | **FILE** | "Captured. Filed. Cross-referenced with what was already there." |
| 5 | 18.85 – 20.85 | **LATER** | *silent — the breather is the point* |
| 6 | 20.45 – 31.45 | **HAND OFF** | "Claude opens with the full context — meeting, recipient, tone, source doc." |
| 7 | 31.15 – 40.65 | **KEPT** | "The promise becomes a thing that's done." |
| 8 | 40.15 – 42.67 | **END CARD** | *silent — let it land* |

Total: 42.67s. Magic beat (frames 3, 4, 6, 7) = ~30s = 70% of total. Reveal (frame 2) = 3.5s. Hook (frame 1) = 4.5s. Promise (frame 8) = 2.5s. Breather (frame 5) = 2s.

### Click chain
4 clicks (2.55s, 17.35s, 30.30s, 38.55s) — each triggers the next scene.

### What this version teaches that the screen-catalogue version didn't

The viewer leaves knowing:
- A specific person (David) made a specific request (rollout setup guide)
- Syncore captured it during a specific meeting (Vertex Labs sync)
- Claude wrote the response with full context
- The promise was kept

vs. the screen-catalogue version where they leave knowing "Syncore has a Today view, an All Actions view, and a Meetings view, all in warm beige."

This is the difference between a video that gets re-shared and a video that gets scrolled past.
