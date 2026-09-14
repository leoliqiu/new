# Retrieval and directory organization

## Default: index plus lexical retrieval

Use existing structure. For a new knowledge base, a practical layout is `index.md`, `knowledge/`, `requirements/`, `workflows/`, `access/`, `rules/`, `preconditions/`, `issues/`, `tests/`, `sources.md`, `questions.md`, `resolved-questions.md`, and `history.md`. Small collections can use flat files. Do not create empty directories just to match this example.

The root index should map subjects and IDs to canonical files, with aliases, short scope descriptions, and “read this when” hints. Subindexes are useful when a directory becomes difficult to scan. Maintain a relationship table where useful: `From ID | Relationship | To ID | Source`. Relations include requires, governed-by, transitions-to, verifies, blocked-by, supersedes, and affected-by.

Retrieval sequence:

1. Read the index and map the question to domain terms, aliases, IDs, release, and environment.
2. Use `rg -n -i` over relevant Markdown paths with literal searches where possible. Search exact IDs/formula terms as well as natural-language synonyms.
3. Read complete matching sections including table headers, exceptions, and nearby definitions. Follow source links and dependency IDs to obtain requirements, preconditions, access rules, and oracles.
4. Filter by applicability and effective version. Retrieve historical or conflicting records when the question requires them.
5. Cite canonical paths plus headings/IDs. If evidence is insufficient, widen the search and then report the gap; absence from top results is not proof of absence.

This is a local retrieval-augmented workflow without an embedding service. Markdown remains usable without infrastructure.

## Optional full-text or vector retrieval

Add a derived SQLite FTS index when repeated searches across many files are materially slow or cumbersome. Add embeddings only when measured synonym/paraphrase retrieval remains weak or the user requests vectorization. Honor an existing search stack. Do not install infrastructure or send content to an external embedding provider merely because RAG was mentioned as one option.

For an implemented index, keep a manifest of relative paths, content hashes, parser version, indexing version, and last indexed timestamp. Chunk by record/heading, keeping a heading breadcrumb and stable record ID. Split oversized sections with bounded overlap, repeating relevant table headers and preserving formula context. Store chunk ID, record ID, path, heading, source references, applicability, status, classification, hash, and text. Line numbers are rebuildable locations, not stable identities.

Incremental updates must replace changed chunks and purge moved/deleted chunks, deduplicate unchanged content, and invalidate results when the source hash differs. Write a replacement index before swapping it into service. Store rebuildable artifacts outside the canonical Markdown search scope.

For vectors, record embedding model/version and dimensionality. A model change requires a compatible rebuild. Combine lexical matching for IDs and exact rules with semantic retrieval for paraphrases; rank and then follow dependency links. Return source excerpts and citations rather than embedding-only summaries. Restrict retrieval to the caller's permitted corpus before returning text; metadata labels alone do not enforce authorization. Application permission documentation and permissions to read the knowledge base are separate concerns.

Before calling retrieval successful, test a small representative query set: exact requirement ID, workflow alias, denied action, formula edge case, exception path, and unanswerable question. Verify the correct source and its necessary context are returned. Record observed misses and improve only as needed. Do not select arbitrary corpus-size thresholds as proof that vectorization is required.
