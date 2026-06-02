# miniR API

Default base URL: `http://localhost:8765`

## Health

`GET /health`

Use this to confirm the miniR service is running before retrieval.

## Retrieve

`POST /retrieve`

Request body:

```json
{
  "query": "question or retrieval query",
  "top_k": 5,
  "use_rerank": true
}
```

Response:

- Content type: `text/plain; charset=utf-8`
- Body: evidence text intended to be inserted into an LLM context.
- Image references, when present, are returned as local filesystem paths.

## Curl Example

```bash
curl -s -X POST http://localhost:8765/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query":"DDPG 算法原理","top_k":5,"use_rerank":true}'
```
