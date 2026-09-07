# Interaction harness

Local, deterministic interaction surface for the LS-01 first slice
(see `../first_slice.md`). Owner: learning-support experiment (LS-08).
Status: minimal harness/API layer over existing contracts; not a product
UI, chat interface, onboarding flow, or live performance feedback.

## What it does

`src/interaction/session.py` (`InteractionSession`) composes existing
components without new inference:

- `learner_context`: `ContextStore`, `AssistanceRequest`, `JournalEntry`
  (request intent, verbatim reports, permissions, selection).
- `passage_practice.passages.investigate`: `manual_investigation` /
  `whole_piece_investigation` (user-selected entry, no difficulty gate).
- `passage_practice.observations`: `observe_pitch_transitions` (LS-06 facts).
- `passage_practice.aids`: `suggest_transition_practice` (LS-07 grounded aid).

Paths exercised (all deterministic, synthetic data only):

- `request_help` for a selected passage with no saved history.
- `request_help` for a selected passage with permitted saved context
  (`ContextScope.REFERENCED` / `PERMITTED`); reports arrive as
  `report_refs` only and never alter observation values.
- `save_note` stores a journal entry without generating any aid.
- `inspect_context` shows current saved/session entries and current
  summaries; nothing hidden is used.
- `correct_note` / `delete_note` / `set_excluded` delegate to the store:
  corrections supersede (old revision dated, never selected), deleted or
  excluded entries are never selected again.
- `request_help` with `ContextScope.NONE` selects empty context even when
  saved entries exist.

The harness accepts already-loaded score objects (no MusicXML parsing
here). Missing scores, missing regions, and unresolvable intervals yield
an aid-shaped abstention (`suggestion=None`) with explicit rationale,
limitations, and diagnostics — never a learner diagnosis and never a
guess. Free text is kept verbatim; no model is called; no traits inferred.

## Boundaries

- Score facts, observations, aid output, and learner reports stay in
  separate fields of `HelpResponse` (`investigation`, `observations`,
  `result`, `selected`).
- No new versioned wire contract: the harness returns live objects and
  adds no serialization schema.
- No persistence beyond the store's explicit JSON save/load; no network.
