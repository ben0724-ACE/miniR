# Examples

## Check Service

```bash
python skill/minir-retrieval/scripts/health_check.py
```

With a custom endpoint:

```bash
python skill/minir-retrieval/scripts/health_check.py --base-url http://localhost:8765
```

## Retrieve Evidence

```bash
python skill/minir-retrieval/scripts/retrieve.py --query "DDPG 算法原理" --top-k 5 --rerank
```

Disable reranking:

```bash
python skill/minir-retrieval/scripts/retrieve.py --query "设备调试步骤" --top-k 8 --no-rerank
```

## Format Saved Evidence

```bash
python skill/minir-retrieval/scripts/format_context.py --input evidence.txt
```

## Agent Prompt Pattern

```text
Use miniR to retrieve local evidence for the user's question. Answer only from relevant evidence. If the evidence is insufficient, say so.
```
