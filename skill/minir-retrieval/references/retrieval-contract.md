# Retrieval Contract

## When to Retrieve

Retrieve before answering when the user asks about information likely to live in local miniR-indexed documents, internal notes, manuals, research files, reports, or document-linked images.

Do not retrieve for general knowledge questions unless the user asks to use the local knowledge base.

## How to Answer

- Treat miniR output as evidence, not as final prose.
- Prefer evidence-backed statements.
- Cite document names or titles when useful.
- If evidence is absent or unrelated, say the knowledge base does not provide enough support.
- Do not invent missing facts, document names, page details, image contents, or file paths.

## Image Paths

miniR may return local image paths associated with a chunk. These paths identify document-linked images. Do not describe image contents unless an image-reading tool has opened the file or the text evidence describes the image.

## Failure Handling

If miniR is unreachable, ask the user to start `python fastapi_server.py` or continue without local knowledge only when the user explicitly allows it.
