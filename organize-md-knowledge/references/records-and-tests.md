# Canonical records and test derivation

Use existing metadata where available. Otherwise assign stable prefixes such as REQ, WF, ACL, CALC, PRE, ISS, SCN, TC, GAP, SRC, and CHG. A record needs ID, title, type, status, evidence state, scope/release, source references, and related IDs. Include owner and effective date when known; unknown administrative metadata should not generate noisy blocking questions unless it matters to the task.

Use explicit headings and concise tables. A rule belongs in one canonical location; other documents reference it. Separate a normative requirement from the evidence of what the system currently does.

## Content by type

| Type | Capture when relevant |
| --- | --- |
| Knowledge | Purpose, definitions, entities, fields, relationships, business meaning, aliases |
| Requirement | Actor, obligation, scope, trigger, acceptance criteria, exceptions, authority and effective version |
| Workflow | Start state, trigger, actors, ordered transitions, guards, actions, next state, approvals, rejection/rework/cancel paths, notifications and audit effects |
| Access | Role/group, resource/action, record scope, field scope, workflow state, allow/deny/unknown, ownership, delegation, precedence and separation of duties |
| Calculation | Formula, variable definitions/types/units, allowed inputs, precision, rounding mode and stage, null/zero behavior, aggregation/filter order, time/currency basis, recalculation trigger, examples |
| Precondition | Required state, actor permissions, environment/configuration, dependencies, test data, setup procedure, verification, reset/cleanup |
| Issue | Expected versus observed behavior, evidence, impacted scope, status, impact, workaround, related requirement and regression tests |

Do not interpret unspecified permissions as denied or infer precedence between competing grants. Do not choose rounding, division-by-zero behavior, calendar basis, or null coercion by convention. Missing consequential semantics become questions.

## Efficient test generation

Start with `SCN ID | Purpose | Requirement/rule IDs | Actor | PRE IDs | Data partition | Expected outcome/source | Risk | Readiness | GAP/issue IDs | TC IDs`. Assess applicable coverage for happy path, invalid inputs, boundaries, permissions, workflow transitions, calculations, recovery, and known-defect regression. Do not manufacture irrelevant scenario categories.

For each executable case use:

```markdown
## TC-001 — Specific behavior
- Scenario: SCN-001
- Requirements/rules: REQ-001, CALC-001
- Sources: source file and section/version
- Actor and scope: ...
- Readiness: ready | blocked | needs-review
- Approval: draft (unless approval evidence exists)
- Environment/build: known value or required constraint
- Preconditions: PRE IDs plus case-specific setup and verification
- Data: concrete synthetic values or a named parameter row

| Step | Action/input | Observable expected result | Rule/source |
| --- | --- | --- | --- |
| 1 | ... | ... | ... |

- Cleanup: ...
- Blockers: GAP IDs or none
- Execution: not run
```

Keep execution evidence separately dated with actual result, build, tester, and evidence location. Preserve imported execution history. A known defect can make a ready test fail; it does not make the incorrect behavior the expected result.

Parameterize cases with the same setup, action structure, and oracle. Split scenarios with different behavioral goals or state sequences. Use equivalence classes and boundary values to reduce duplication. Pairwise combinations can reduce independent low-risk combinations, but must not replace explicit access-denial, separation-of-duties, critical workflow, or calculation-boundary checks.

Reuse PRE records for setup; keep setup actions in the test when setup itself is under test. Specify how to verify preconditions before execution and isolate/reset data between parameter rows. Missing critical setup makes the case blocked; do not count it as executable coverage.

For calculations, select representative and boundary inputs, independently derive expected outputs, and state intermediate values when rounding order matters. Use decimal arithmetic for exact monetary examples when appropriate to the rule. Do not derive the oracle solely from the same implementation being tested. Source-backed algebraic properties may supply additional checks; label unsupported properties as proposals.

Maintain `Requirement/rule ID | Acceptance criterion/branch | Scenario IDs | Case IDs | Coverage status | Gap IDs`. Use statuses such as covered-ready, covered-blocked, uncovered, or not-applicable-with-reason. Review each relevant criterion and branch, not just each requirement ID. Distinguish designed coverage from execution/pass coverage. Follow changed rules through this table to identify retests.
