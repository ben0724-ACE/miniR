# Changelog

All notable changes to miniR are documented in this file.

## v0.1.0 - 2026-06-02

### Added

- Multi-format document ingestion for Markdown, Word, PowerPoint, Excel and PDF.
- Unified parser output for text chunks, document format, images and image maps.
- Web UI review flow for scanning, previewing, editing and confirming chunks.
- Local hybrid retrieval with SQLite, FAISS, BM25, dense embeddings, sparse embeddings and optional reranking.
- Agent Skill package at `skill/minir-retrieval`.
- Parser tests for Markdown, Word, PowerPoint, Excel, PDF and document image handling.
- GitHub project files: English and Chinese README, MIT License, contributing guide, changelog, issue templates and test workflow.

### Changed

- Standalone image files are no longer indexed as documents. Images are preserved only when referenced by or embedded in supported documents.
- Duplicate document detection uses relative path and format instead of filename alone.

### Known Limitations

- OCR is not supported.
- Image content is not semantically searchable.
- Excel parsing is sheet-oriented and does not perform complex table region detection.
