# Answerable gaps

`questions.md` is the user-editable queue, not a list regenerated destructively each run. Preserve user answers and stable IDs. Match potential duplicates by subject, scope, and missing decision, not only wording.

```markdown
# Open questions

Enter your answer in the Answer column. Include a source or decision date when available. Partial answers remain open until the missing details are resolved.

| Gap ID | Topic/affected IDs | Question | Why needed/blocked work | Evidence/context | Owner/priority | Answer | State |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GAP-001 | CALC-001 | Which rounding mode and stage apply? | Exact expected results are blocked | Source describes two decimal places only | Unknown / high | | open |
```

For complex answers, link a `## GAP-001` section below the table and allow prose there. In table cells escape literal pipes. Questions should be answerable: ask for the missing decision with concrete context, units, examples, or conflicting alternatives. Group related missing facts without making unrelated blockers depend on one enormous question.

Lifecycle:

1. **open**: missing information or unresolved contradiction; question has no usable answer.
2. **answered-pending**: answer received; assess completeness, scope, source authority, and consistency. Treat user answers as user-supplied evidence without inventing formal approval. If an answer contradicts a controlled requirement, retain the conflict unless the user's authority or a supporting decision resolves it.
3. **partial/conflict**: incorporate supported independent details; preserve the original question/answer and specify the remaining question. Keep it in the open table.
4. **resolved**: update canonical records, relevant tests/preconditions and coverage, source register, and change history. Append the original question, answer, resolution date, evidence, and destination IDs/paths to `resolved-questions.md` or the existing resolution log. Only then remove its row from the open table. Resolve blockers individually; a case stays blocked if any critical blocker remains.

If a run fails mid-update, retain the open row until reconciliation verifies the canonical update and resolution entry. A rerun must reconcile by GAP ID without duplicating entries. Never remove a gap merely because Answer is nonempty. An answer such as “not applicable” requires scope and rationale.

When new evidence invalidates a resolution, reopen the same gap with a dated event and new question while retaining its resolution history. For changes genuinely about a different scope or decision, create a new gap linked to the prior one.

The final summary should count remaining gaps and tell the user where to answer. Do not ask every question again in chat when the editable file already contains them.
