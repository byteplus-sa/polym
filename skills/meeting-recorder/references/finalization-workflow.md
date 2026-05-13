# Finalization Workflow

The recorder must finish three persistence layers after recording:

1. Syncore finalized meeting note
2. SA Lark Wiki via `sa-wiki`
3. Local wiki when available

Do not call this "dual write" in user-facing messages.

## Strict Order

```text
end_session
  -> compose summary/action_items/follow_ups
  -> finalize_meeting
  -> save to SA knowledge base via sa-wiki
  -> update local wiki when available
```

## Summary Shape

The AI summary should include:

- Meeting context and purpose
- Key discussion points
- Decisions
- Customer feedback
- Feature asks
- Technical issues
- Risks
- Action items
- Follow-ups

Only include sections that are supported by the transcript.

## Lark Wiki Save

Delegate to `sa-wiki`:

- CREATE a meeting page when this meeting is new.
- APPEND customer TIMELINE when a customer is identifiable.
- CREATE/APPEND feedback or issue pages only when the point is reusable beyond this meeting.

Do not copy Bitable constants into this skill. `sa-wiki` owns that contract.

## Local Wiki Save

Follow the user's local wiki schema:

- `raw/meeting-<slug>-<date>.md`: transcript or transcript pointer
- `wiki/sources/meeting-<slug>-<date>.md`: source page with summary and citations
- `wiki/entities/customers/<customer>.md`: recent interaction row when applicable
- `wiki/log.md`: append-only ingest log

If no local wiki exists, ask once whether to create it.

## Failure Recovery

If Syncore finalization succeeds but knowledge-base save fails, tell the user:

```text
The recording and summary are finalized. Saving to the SA knowledge base needs a retry.
```

If local wiki update fails, do not fail the meeting finalization. Tell the user the meeting summary is saved to the main knowledge base and local wiki update can be retried.

