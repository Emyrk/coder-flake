#!/usr/bin/env python3
"""Download seed GitHub search data for coder/coder flake research.

This intentionally uses only unauthenticated GitHub Search API calls, so it
collects a broad seed set without requiring Steven to hand Hermes a token.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
PROCESSED = ROOT / "processed"
RAW.mkdir(parents=True, exist_ok=True)
PROCESSED.mkdir(parents=True, exist_ok=True)

QUERIES = [
    {"name": "issues-flake-title", "q": "repo:coder/coder type:issue flake in:title"},
    {"name": "issues-flaky-title", "q": "repo:coder/coder type:issue flaky in:title"},
    {"name": "prs-flake-title", "q": "repo:coder/coder type:pr flake in:title"},
    {"name": "prs-flaky-title", "q": "repo:coder/coder type:pr flaky in:title"},
]

HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "Hermes-coder-flake-research",
}


def request_json(url: str) -> tuple[dict, dict[str, str]]:
    req = urllib.request.Request(url, headers=HEADERS)
    while True:
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                headers = {k.lower(): v for k, v in r.headers.items()}
                return json.load(r), headers
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            if e.code in (403, 429):
                reset = e.headers.get("x-ratelimit-reset")
                wait = 65
                if reset and reset.isdigit():
                    wait = max(5, int(reset) - int(time.time()) + 3)
                print(f"rate limited on {url}; sleeping {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            raise RuntimeError(f"GET {url} failed: HTTP {e.code}: {body[:500]}") from e


def search_all(query: str) -> list[dict]:
    items: list[dict] = []
    page = 1
    total = None
    while True:
        params = urllib.parse.urlencode({"q": query, "per_page": 100, "page": page})
        url = f"https://api.github.com/search/issues?{params}"
        data, headers = request_json(url)
        if total is None:
            total = data.get("total_count")
        batch = data.get("items", [])
        items.extend(batch)
        remaining = headers.get("x-ratelimit-remaining")
        print(f"{query!r}: page {page}, got {len(batch)}, accumulated {len(items)}/{total}, search_remaining={remaining}")
        if len(batch) < 100 or len(items) >= min(total or 0, 1000):
            break
        page += 1
        # Unauthenticated search is 10 requests/minute. Stay boring.
        time.sleep(7)
    return items


def main() -> int:
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    manifest = {"downloaded_at": now, "repo": "coder/coder", "queries": QUERIES}
    all_records: dict[int, dict] = {}
    per_query_counts = {}

    for spec in QUERIES:
        items = search_all(spec["q"])
        per_query_counts[spec["name"]] = len(items)
        (RAW / f"{spec['name']}.json").write_text(json.dumps({"query": spec, "downloaded_at": now, "items": items}, indent=2), encoding="utf-8")
        for item in items:
            n = item["number"]
            rec = all_records.setdefault(n, item)
            rec.setdefault("matched_queries", [])
            rec["matched_queries"].append(spec["name"])

    records = sorted(all_records.values(), key=lambda r: ("pull_request" in r, r["number"]))
    manifest["per_query_counts"] = per_query_counts
    manifest["unique_records"] = len(records)
    manifest["unique_issues"] = sum(1 for r in records if "pull_request" not in r)
    manifest["unique_prs"] = sum(1 for r in records if "pull_request" in r)
    (RAW / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (RAW / "all-title-matches.json").write_text(json.dumps(records, indent=2), encoding="utf-8")

    with (PROCESSED / "title_matches.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "number", "kind", "state", "title", "url", "created_at", "updated_at", "closed_at", "user", "labels", "comments", "matched_queries",
        ])
        w.writeheader()
        for r in records:
            w.writerow({
                "number": r["number"],
                "kind": "pr" if "pull_request" in r else "issue",
                "state": r.get("state", ""),
                "title": r.get("title", ""),
                "url": r.get("html_url", ""),
                "created_at": r.get("created_at", ""),
                "updated_at": r.get("updated_at", ""),
                "closed_at": r.get("closed_at", ""),
                "user": (r.get("user") or {}).get("login", ""),
                "labels": ";".join(l.get("name", "") for l in r.get("labels", [])),
                "comments": r.get("comments", 0),
                "matched_queries": ";".join(r.get("matched_queries", [])),
            })

    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
