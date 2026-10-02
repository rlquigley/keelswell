---
name: open-question-story-1-1
description: "OPEN, unresolved: story 1.1 (wave 1A) -- should subtract refuse a result below zero or clamp it to 0?"
metadata:
  type: project
---

OPEN QUESTION, unresolved as of 2026-09-30. Tagged: story 1.1, wave 1A.

Story 1.1's AC-2 says `calc.subtract` raises `ValueError` when `b` is greater
than `a`. On 2026-09-29 the founder said in passing that going below zero
"might be better clamped to 0 instead". No ruling was made. The two readings
produce different tests and different code.

**Why:** building either reading without a ruling means rework if the founder
picks the other.

**How to apply:** the founder answers this before story 1.1 is implemented.
Do not pick a reading.
