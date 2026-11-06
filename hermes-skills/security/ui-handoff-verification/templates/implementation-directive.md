# Implementation directive — must-follow (for the receiving AI coder)

> Paste this (or the packaged version) at the top of the agent's task. It is the contract; violations are failures.

## Your three red lines (never cross)
1. **No UI invention.** Do not change/redesign any frontend UI — layout, colors, radius, font sizes, spacing, copy, icons, interaction patterns are all defined by the baseline spec + baseline file. Copy them item by item. Any idea you have for "better" is forbidden to ship.
2. **Baseline wins on conflict.** Spec document vs baseline file conflict → baseline file wins (it is interactive, the only arbiter). When your output differs from baseline, change YOUR output — never change the baseline.
3. **Your scope = backend integration + engineering.** The UI's look is decided by the baseline; you make it run, connect the backend, and — when a backend task requires it — do the MINIMAL frontend adaptation (bind data, fill fields). Do not touch styles, layout, copy, or interaction structure.

## Your current task list
- **A. Rebuild UI (one-time, copy the baseline):** read the golden spec + baseline file; recreate every page so visuals/interactions match; until backend is ready, fill UI with baseline demo data so pages are viewable and clickable.
- **B. Backend integration:** map backend fields to the spec's data model (statuses, money rules, state machines — see spec "business rules", marked 勿回退). When mapping data into UI: replace data values only, never change UI structure.
- **C. Deploy:** static hosting or Docker, hash routing. Verify after deploy (spec acceptance checklist).

## Change management flow (every future UI change)
UI changes ALWAYS happen on the baseline file (the user/maintainer edits it) — never start from your code.
1. Read the latest baseline file, locate the change.
2. Sync YOUR implementation to match the baseline (copy, don't reimagine).
3. Do the backend adaptation only if the change involves data (new fields/status/endpoints).
4. Forbidden: refactoring styles, touching other UI, adding your own components/copy/effects.
5. Acceptance: screenshot comparison vs baseline; UI must match; backend flow verified.

One-sentence test: "Whatever the baseline file looks like, your code must look exactly like it; backend work is yours, UI decisions are the baseline's."

## Pitfalls you have hit before (do not repeat)
- Don't rebuild pages "in your own style" (user: output differing from baseline = failure).
- Don't invent components, animations, or copy.
- Don't touch the English copy (finalized).
- Don't alter the money model (no platform commission; withdrawal fee uniform 1.5%; deposit = balance-transfer only, non-refundable, excess unfrozen can transfer back).
- Funds center is LIST-SELECT style (click a row → the panel shows directly below the list) — not accordion, not split columns, not right panel.
- Use hash routing (`#/funds`), not path routing (404 on static hosts).

## Working posture
- Read the baseline file/spec section before touching code.
- Every delivery: report what you changed, split into (UI sync) + (backend adaptation).
- Unsure how a UI should behave → open the baseline file and copy its behavior. Don't guess.
