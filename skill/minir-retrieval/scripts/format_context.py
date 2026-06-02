#!/usr/bin/env python3
"""Wrap miniR retrieval text as an LLM context block."""

import argparse
import sys
from pathlib import Path


def read_input(path: str | None) -> str:
    if path:
        return Path(path).read_text(encoding="utf-8-sig")
    return sys.stdin.read()


def main() -> int:
    parser = argparse.ArgumentParser(description="Format miniR evidence text for LLM context.")
    parser.add_argument("--input", help="Path to a saved miniR retrieval response. Reads stdin when omitted.")
    parser.add_argument("--title", default="miniR knowledge-base evidence", help="Context block title.")
    args = parser.parse_args()

    text = read_input(args.input).strip()
    if not text:
        print("No miniR evidence was provided.", file=sys.stderr)
        return 1

    print(f"## {args.title}")
    print()
    print(text)
    print()
    print("Use the evidence above when it is relevant. If it is insufficient, say so explicitly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
