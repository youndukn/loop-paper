# Impact Scoring

Impact score must be evidence-based. Agents may calculate or propose a score, but must not invent human grade or measured outcomes.

## Recommended Formula

Use a 0-10 score:

```text
impact_score =
  0.25 * downstream_reference_score +
  0.25 * validation_strength_score +
  0.25 * human_grade_score +
  0.25 * measured_outcome_score
```

If a component is unavailable, mark it `TBD` instead of fabricating it.

## Component Guidance

Downstream reference score:

- 0: no references
- 3: referenced by one planned paper
- 6: referenced by accepted papers
- 10: foundational dependency for many accepted papers

Validation strength score:

- 0: no validation
- 3: implementation checks only
- 6: tests or measurable evidence
- 10: independent validation plus real-world outcome

Human grade score:

- Must come from an explicit human or superior grade.
- Leave `TBD` when missing.

Measured outcome score:

- Must come from metrics, observed user behavior, revenue, cost, quality, safety, or another concrete outcome.
- Leave `TBD` when missing.
