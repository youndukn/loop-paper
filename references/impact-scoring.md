# Impact Scoring

Impact score must be evidence-based. Agents may calculate or propose a score, but must not invent measured outcomes.

## Recommended Formula

Use a 0-10 score:

```text
impact_score =
  0.33 * downstream_reference_score +
  0.33 * validation_strength_score +
  0.34 * measured_outcome_score
```

If a component is unavailable, mark it `TBD` instead of fabricating it.

## Component Guidance

Downstream reference score:

- 0: no references
- 3: referenced by one planned paper
- 6: referenced by accepted papers
- 10: foundational dependency for many accepted papers

Only positive downstream edges count for this component: `References`,
`Depends on`, and `Extends`. `Contradicts` and `Supersedes` remain graph
relationships, but they do not raise the impact score.

Validation strength score:

- 0: no validation
- 3: implementation checks only
- 6: tests or measurable evidence
- 10: independent validation plus real-world outcome

Measured outcome score:

- Must come from metrics, observed user behavior, revenue, cost, quality, safety, or another concrete outcome.
- To make the deterministic scorer use the component, include an explicit
  0-10 score in the `Measured outcome:` basis line, for example
  `Measured outcome: score=8/10; latency dropped from 400ms to 250ms`.
- Leave `TBD` when missing.
