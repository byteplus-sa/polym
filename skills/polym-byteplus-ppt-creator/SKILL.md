---
name: polym-byteplus-ppt-creator
description: Create, redesign, or polish editable BytePlus-branded PowerPoint decks using a bundled 20-slide template with mapped slide catalog, starter deck script, and PPTX validator. Use for BytePlus presentations, proposals, or workshop decks.
---

# BytePlus PPT Creator

Create presentation-ready, editable BytePlus decks that use the supplied template as a real design system rather than as a decorative background.

## Bundled resources

- `assets/BytePlus Presentation Template_FEB 2026.pptx` is the canonical editable source template.
- `references/template-slide-catalog.json` maps every source slide, its visible text, layout role, editability, and recommended use.
- `references/template-slide-catalog.schema.json` defines the catalog's machine-readable contract.
- `references/artifact-tool-authoring.md` provides the imported-template authoring pattern.
- `scripts/create_starter_deck.mjs` creates a clean editable starter deck from selected template slide numbers.
- `scripts/validate_byteplus_pptx.py` checks PPTX package integrity, dimensions, slide count, font references, and unresolved placeholder text.

Treat paths as relative to this skill directory. Do not rely on a separate copy of the template elsewhere on the machine.

## Outcome contract

Deliver a `.pptx` that:

- uses the BytePlus template's 16:9 canvas, masters, layouts, theme, logos, footer treatment, and Byte Sans typography;
- keeps text, tables, charts, diagrams, and other evidence editable when PowerPoint supports native editing;
- chooses source layouts intentionally from the mapped catalog;
- uses concise, audience-appropriate writing without invented facts or unsupported claims;
- cites researched claims and third-party assets in the relevant slide's speaker notes;
- contains no accidental template placeholders, clipped text, unintended overlap, distorted logos, or broken media;
- has been rendered and visually inspected slide by slide before delivery.

## Clarify the brief

Extract available answers from the conversation and supplied files before asking questions. Confirm only missing details that would materially change the deck:

- audience and presentation setting;
- objective or decision the deck must support;
- required content, sources, and factual boundaries;
- total slide count, presentation duration, and output destination;
- whether the user wants a new deck, an edit, or a redesign;
- visual tone beyond the BytePlus brand;
- confidentiality, customer-data, and sharing constraints.

When the user provides enough context, proceed with reasonable assumptions and state consequential ones briefly.

## Inspect and select template slides

Read `references/template-slide-catalog.json` directly before planning a deck. Select candidate slides from their `template_role`, `usage_guidance`, `visual_description`, and `editable_elements` metadata. The catalog is deliberately structured so the agent can reason over it without an intermediate query tool.

Build an internal slide plan with, at minimum:

- target slide number;
- communication purpose;
- source template slide number;
- required content and evidence;
- intended visual asset or native chart/table;
- speaker-note citations;
- density and risk notes.

Choose the smallest set of layouts that supports the narrative. Use the source slide's `template_role`, `usage_guidance`, and `editable_elements` fields as design evidence. A template slide number identifies a visual starting point, not mandatory copy.

Create a starter deck from the selected source slides after resolving the bundled Node.js paths:

```bash
RUNTIME_NODE_MODULES=/absolute/path/to/node_modules \
/absolute/path/to/node scripts/create_starter_deck.mjs \
  --slides 1,3,7,11,13,20 \
  --output /absolute/path/to/starter.pptx
```

## Authoring workflow

1. Work on a copy of the bundled template. Never overwrite the bundled asset.
2. Import the PPTX with `@oai/artifact-tool` using JavaScript ES modules.
3. Preserve the source dimensions of `12192000 x 6858000` EMU, equivalent to a 16:9 slide.
4. Reuse or duplicate mapped source slides and edit existing elements in place when practical.
5. Keep the template's masters, layouts, theme colors, BytePlus logo treatment, bottom gradient, page markers, and intended font hierarchy.
6. Remove unused placeholders from selected slides. Do not hide placeholder text behind new objects.
7. Fit content by editing copy or choosing a better mapped layout before shrinking text.
8. Keep required tables, charts, and diagrams as native slide objects. Use raster images for photographic or illustrative visuals, not for evidence that needs editing.
9. Put source URLs and concise provenance in speaker notes on the slide that uses the claim or asset.
10. Export to a new draft path, validate it, render every slide, repair issues, and then save a separate final PPTX.

Use the bundled workspace runtime when available. Do not install replacement presentation libraries or use `python-pptx` for deck creation or editing.
Read `references/artifact-tool-authoring.md` before writing the authoring module.

## BytePlus design system

The template catalog records source-slide specifics. Apply these deck-wide principles:

- Keep the white canvas, black text, BytePlus blue, violet, cyan, coral, and navy accents unless the user explicitly asks for another approved treatment.
- Preserve the BytePlus logo's proportions and clear space.
- Use Byte Sans Regular, Medium, and Bold when present in the source and available in the runtime.
- Keep title slides minimal. Prefer one strong title, a short subtitle or context line, and one purposeful visual.
- Use section dividers to signal a real narrative transition.
- Prefer one coherent composition over dashboard-like card grids unless the mapped source layout or content specifically calls for cards.
- Use strong images at intentional crops. Do not stretch images or reuse the same decorative image across multiple slides by default.
- Use the template's icon and illustration library only when the symbol's meaning is clear and relevant.
- Keep footer text and page numbers consistent across content slides.

## Writing and evidence

- Name each slide's subject directly. Use a factual takeaway title only when the evidence supports it.
- Use plain, specific language. Remove generic slogans, filler kickers, and exaggerated marketing claims.
- Avoid em dashes, semicolons, decorative dot-separated phrases, formulaic three-part lists, passive voice, and repeated "not X, but Y" framing.
- Preserve units, comparison bases, dates, and caveats when summarizing quantitative evidence.
- Label hypotheses, estimates, illustrative data, and product limitations explicitly.
- Never invent customer names, results, product capabilities, compliance claims, prices, release dates, or performance figures.
- Use public URLs or audience-accessible shared resources in shared decks. Do not cite local filesystem paths in audience-facing slides or notes.

## Visual assets

Use official BytePlus or user-supplied assets when available. For external images, capture the direct source URL, creator or organization when available, access date, license or usage basis, and whether the asset was modified. For generated visuals, record the model, prompt, generation date, and whether the image is illustrative.

Do not present generated visuals as real customer evidence, actual product output, or event photography. Preserve original logos and evidence images without distortion.

## Validation

Run the bundled validator on every candidate deck:

```bash
python3 scripts/validate_byteplus_pptx.py /absolute/path/to/candidate.pptx --json /absolute/path/to/validation.json
```

Treat a non-zero exit as a hard failure. Review warnings individually. Template placeholder warnings are expected on the source template but should normally be absent from a finished deck.

Then complete a visual and functional review:

1. Render every final slide at readable resolution.
2. Inspect each slide individually, then review a contact sheet for narrative rhythm and consistency.
3. Compare reused layouts with their mapped source slides.
4. Check for clipping, overflow, overlap, broken crops, distorted logos, inconsistent footers, unreadable citations, and unresolved placeholders.
5. Confirm slide count, content coverage, factual accuracy, citations, editability, and asset provenance.
6. Re-import the final PPTX with `@oai/artifact-tool` to confirm it remains parseable.
7. Open the deck in PowerPoint only when available and only claim PowerPoint validation if it was actually inspected there.

Structural validation cannot prove visual quality, factual accuracy, accessibility, or compatibility with every PowerPoint version. Report any uncompleted review plainly.

## Handoff

Return the final editable PPTX once. Mention only limitations that affect use, such as missing media, unavailable fonts, unresolved evidence, or an incomplete accessibility review. Keep internal build logs, temporary renders, and validation receipts out of the audience-facing deck unless the user requests them.
