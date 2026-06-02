---
name: minir-retrieval
description: Use miniR as a local RAG knowledge-base retrieval backend. Use when an agent needs to answer questions grounded in local miniR-indexed documents, including Markdown, Word, PowerPoint, Excel, PDF content, and document-linked images returned by miniR.
---

# miniR Retrieval

Use miniR before answering when a user request may depend on local knowledge-base documents.

## Workflow

1. If service state is unknown, run `scripts/health_check.py`.
2. Retrieve evidence with `scripts/retrieve.py --query "<user question>" --top-k 5 --rerank`.
3. Use the returned evidence text as grounding context.
4. If evidence is missing, weak, or unrelated, say the knowledge base does not provide enough support.
5. If evidence includes image paths, treat them as local filesystem paths. Do not infer image contents unless an image-reading tool is used.

## Scripts

- `scripts/health_check.py`: check miniR `/health` and print service status.
- `scripts/retrieve.py`: call miniR `POST /retrieve` and print evidence text.
- `scripts/format_context.py`: normalize saved or piped retrieval text for an LLM context block.

All scripts use only Python standard-library modules.

## References

- Read `references/api.md` for miniR endpoint details.
- Read `references/retrieval-contract.md` for answer behavior and evidence handling rules.
- Read `references/examples.md` for command examples and common usage patterns.
