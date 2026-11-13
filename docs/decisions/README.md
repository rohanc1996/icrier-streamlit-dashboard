# Decision log

Short records of methodology choices that are expensive to re-litigate: scaling,
rounding, missing-data handling, indicator treatment, dataset vintages.

One file per decision: `NNNN-short-title.md`.

```markdown
# NNNN — Title

- **Date:** YYYY-MM-DD
- **Status:** proposed | accepted | superseded

## Context

What question came up, and what constraint forced a decision.

## Decision

The rule we now follow, stated so it can be applied without re-deriving it.

## Consequences

What this makes easy, what it makes hard, and where it is enforced in code
(file, function, test).
```

Keep it to one screen. Link the relevant test or module so the rule is
checkable.
