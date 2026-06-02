#!/usr/bin/env python3
"""Check whether a miniR retrieval service is reachable."""

import argparse
import json
import sys
import urllib.error
import urllib.request


DEFAULT_BASE_URL = "http://localhost:8765"


def normalize_base_url(value: str) -> str:
    return (value or DEFAULT_BASE_URL).rstrip("/")


def request_health(base_url: str, timeout: float) -> tuple[int, str]:
    url = normalize_base_url(base_url) + "/health"
    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8", errors="replace")
        return response.status, body


def main() -> int:
    parser = argparse.ArgumentParser(description="Check miniR service health.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"miniR base URL, default: {DEFAULT_BASE_URL}")
    parser.add_argument("--timeout", type=float, default=10.0, help="Request timeout in seconds.")
    args = parser.parse_args()

    try:
        status, body = request_health(args.base_url, args.timeout)
    except urllib.error.URLError as error:
        print(f"miniR health check failed: {error}", file=sys.stderr)
        return 1
    except TimeoutError:
        print("miniR health check timed out", file=sys.stderr)
        return 1

    print(f"miniR health: HTTP {status}")
    if body:
        try:
            print(json.dumps(json.loads(body), ensure_ascii=False, indent=2))
        except json.JSONDecodeError:
            print(body)
    return 0 if 200 <= status < 300 else 1


if __name__ == "__main__":
    raise SystemExit(main())
