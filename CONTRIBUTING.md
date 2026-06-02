# Contributing to miniR

Thanks for improving miniR. This project is a local RAG retrieval backend, so changes should keep the retrieval API stable and avoid adding unnecessary hosted dependencies.

## Development Setup

Use Python 3.12 or newer.

```bash
pip install -r requirements.txt
```

For lightweight parser tests, these packages are enough:

```bash
pip install numpy python-docx python-pptx openpyxl PyMuPDF
```

## Running Tests

```bash
python -B -m unittest discover -s tests
```

Before opening a pull request, also run:

```bash
git diff --check
```

## Contribution Guidelines

- Keep `/retrieve` response fields backward compatible unless the change is explicitly versioned.
- Prefer local, self-hosted dependencies over hosted services.
- Add parser tests when changing document ingestion behavior.
- Do not commit local documents, generated indexes, SQLite databases, model files or extracted image caches.
- Keep README updates in both `README.md` and `README_zh-CN.md` when user-facing behavior changes.

## Commit Style

Use Conventional Commits:

```text
feat(ingestion): support pptx parsing
fix(retrieval): preserve image paths in results
docs(readme): update quick start
```

## Reporting Issues

Use the GitHub issue templates and include:

- miniR version or commit hash
- Python version and operating system
- command or API request used
- expected result and actual result
- logs or sample document details when possible
