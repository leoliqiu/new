Use $organize-md-knowledge to organize and maintain the Markdown knowledge base below.

Target directory: <absolute directory path>
Incoming information: <files, directory, pasted content, or none>
Scope/release: <if known; otherwise determine from sources>
Requested output: organize/update knowledge, maintain questions, and generate scenarios plus executable test steps where the evidence supports them.

Inspect the existing structure and reuse its IDs and conventions. Support both a new collection and an existing directory. Reconcile new content with existing knowledge; preserve sources, history, exceptions, and unresolved contradictions. Organize content around knowledge, requirements, workflows, access control, calculations, preconditions, and known issues.

Use a Markdown index, aliases, cross-references, and targeted full-text search by default. Add a more complex retrieval index only if it solves a demonstrated need. Keep Markdown canonical and refresh retrieval after updates.

Create or update an editable questions.md for missing decisions and gaps. Preserve my answers. On later runs, incorporate complete answers into the canonical records and dependent tests, archive the resolution, and remove only resolved rows from the open table. Keep partial or conflicting answers open with a precise remaining question.

Generate compact, traceable scenarios and reusable preconditions, then parameterized action/expected-result test cases. Cover applicable happy paths, negative paths, permissions, boundaries, workflow transitions, calculations, and known-issue regressions. Do not invent expected behavior. Mark tests blocked when required information is missing. Maintain requirement-to-test coverage and distinguish generated tests from executed results.

Update the Markdown files directly within the requested scope. Verify IDs, links, source traceability, gap transitions, and affected coverage. Report changed files, the retrieval method actually used, checks performed, and where I should answer remaining questions.

## Follow-up: incorporate answers or new material

Use $organize-md-knowledge on <absolute directory path>. Process the answers in questions.md and this new material: <paths or text>. Reconcile the canonical documentation, update affected scenarios and tests, preserve resolution history, remove resolved questions from the open table, and refresh indexes. Leave unrelated content alone.

## Follow-up: retrieve and explain

Use $organize-md-knowledge to answer <question> from <absolute directory path>. Retrieve the relevant requirements and their linked workflows, access rules, calculations, and preconditions. Cite files and record IDs, distinguish current rules from observations, and identify missing evidence.
