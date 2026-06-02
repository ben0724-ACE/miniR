#!/usr/bin/env python3
"""Retrieve evidence from miniR and print the response text."""

import argparse
import json
import sys
import urllib.error
import urllib.request


DEFAULT_BASE_URL = "http://localhost:8765"


def normalize_base_url(value: str) -> str:
    return (value or DEFAULT_BASE_URL).rstrip("/")


def retrieve(base_url: str, query: str, top_k: int, use_rerank: bool, timeout: float) -> str:
    url = normalize_base_url(base_url) + "/retrieve"
    payload = json.dumps({
        "query": query,
        "top_k": top_k,
        "use_rerank": use_rerank,
    }, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(description="Retrieve evidence from miniR.")
    parser.add_argument("--query", required=True, help="User question or retrieval query.")
    parser.add_argument("--top-k", type=int, default=5, help="Number of evidence chunks to retrieve.")
    parser.add_argument("--rerank", action="store_true", help="Enable miniR reranking.")
    parser.add_argument("--no-rerank", action="store_true", help="Disable miniR reranking.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"miniR base URL, default: {DEFAULT_BASE_URL}")
    parser.add_argument("--timeout", type=float, default=60.0, help="Request timeout in seconds.")
    args = parser.parse_args()

    use_rerank = True
    if args.no_rerank:
        use_rerank = False
    elif args.rerank:
        use_rerank = True

    try:
        text = retrieve(args.base_url, args.query, args.top_k, use_rerank, args.timeout)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        print(f"miniR retrieve failed: HTTP {error.code}\n{detail}", file=sys.stderr)
        return 1
    except urllib.error.URLError as error:
        print(f"miniR retrieve failed: {error}", file=sys.stderr)
        return 1
    except TimeoutError:
        print("miniR retrieve timed out", file=sys.stderr)
        return 1

    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
