#!/usr/bin/env python3
"""Expand coder/coder flake research dataset via issue timelines and PR context.

Unauthenticated GitHub API works, but is slow. The script is resumable:
existing raw JSON files are reused, and every successful response is written
immediately before the next request.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
PROCESSED = ROOT / "processed"
RAW_ISSUES = RAW / "issues"
RAW_PRS = RAW / "prs"
RAW.mkdir(parents=True, exist_ok=True)
PROCESSED.mkdir(parents=True, exist_ok=True)
RAW_ISSUES.mkdir(parents=True, exist_ok=True)
RAW_PRS.mkdir(parents=True, exist_ok=True)

REPO = "coder/coder"
API = "https://api.github.com"
USER_AGENT = "Hermes-coder-flake-research"
TIMELINE_ACCEPT = "application/vnd.github.mockingbird-preview+json"
DEFAULT_ACCEPT = "application/vnd.github+json"

ISSUE_REF_RE = re.compile(r"(?<![\w/])#(\d{1,6})(?!\w)")


class RateLimitStop(RuntimeError):
    pass


class Client:
    def __init__(self, token: str | None, max_requests: int | None, min_remaining: int, wait: bool):
        self.token = token
        self.max_requests = max_requests
        self.min_remaining = min_remaining
        self.wait = wait
        self.requests = 0
        self.rate: dict[str, str] = {}

    def headers(self, accept: str = DEFAULT_ACCEPT) -> dict[str, str]:
        h = {
            "Accept": accept,
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": USER_AGENT,
        }
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def get_json(self, path: str, accept: str = DEFAULT_ACCEPT) -> Any:
        if self.max_requests is not None and self.requests >= self.max_requests:
            raise RateLimitStop(f"max request budget reached: {self.requests}")
        url = path if path.startswith("http") else f"{API}{path}"
        attempt = 0
        while True:
            attempt += 1
            req = urllib.request.Request(url, headers=self.headers(accept))
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    self.requests += 1
                    self.rate = {k.lower(): v for k, v in r.headers.items()}
                    remaining = int(self.rate.get("x-ratelimit-remaining", "999999"))
                    if remaining <= self.min_remaining:
                        if self.wait:
                            self._sleep_until_reset("remaining budget low")
                        else:
                            raise RateLimitStop(
                                f"rate remaining {remaining} <= min_remaining {self.min_remaining}; reset={self.rate.get('x-ratelimit-reset')}"
                            )
                    return json.load(r)
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", "replace")
                headers = {k.lower(): v for k, v in e.headers.items()}
                remaining = headers.get("x-ratelimit-remaining")
                if e.code in (403, 429) and (e.code == 429 or remaining == "0"):
                    self.rate = headers
                    if not self.wait:
                        raise RateLimitStop(f"rate limited on {url}; reset={headers.get('x-ratelimit-reset')}") from e
                    self._sleep_until_reset(f"rate limited on {url}")
                    continue
                if e.code >= 500 and attempt < 5:
                    sleep = min(30, 2 ** attempt)
                    print(f"HTTP {e.code} on {url}; retrying in {sleep}s", file=sys.stderr)
                    time.sleep(sleep)
                    continue
                raise RuntimeError(f"GET {url} failed: HTTP {e.code}: {body[:500]}") from e
            except (TimeoutError, OSError) as e:
                if attempt < 5:
                    sleep = min(30, 2 ** attempt)
                    print(f"network error on {url}: {e}; retrying in {sleep}s", file=sys.stderr)
                    time.sleep(sleep)
                    continue
                raise

    def _sleep_until_reset(self, reason: str) -> None:
        reset = self.rate.get("x-ratelimit-reset")
        wait = 65
        if reset and reset.isdigit():
            wait = max(5, int(reset) - int(time.time()) + 3)
        wait = min(wait, 3900)
        print(f"{reason}; sleeping {wait}s", file=sys.stderr)
        time.sleep(wait)

    def get_all_pages(self, path: str, accept: str = DEFAULT_ACCEPT) -> list[Any]:
        out: list[Any] = []
        page = 1
        while True:
            sep = "&" if "?" in path else "?"
            data = self.get_json(f"{path}{sep}per_page=100&page={page}", accept=accept)
            if not isinstance(data, list):
                raise RuntimeError(f"expected list from {path}, got {type(data).__name__}")
            out.extend(data)
            if len(data) < 100:
                return out
            page += 1


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def cached(path: Path) -> Any | None:
    if path.exists() and path.stat().st_size > 0:
        return read_json(path)
    return None


def fetch_cached(client: Client, path: Path, api_path: str, accept: str = DEFAULT_ACCEPT) -> Any:
    data = cached(path)
    if data is not None:
        return data
    data = client.get_json(api_path, accept=accept)
    write_json(path, data)
    return data


def fetch_pages_cached(client: Client, path: Path, api_path: str, accept: str = DEFAULT_ACCEPT) -> list[Any]:
    data = cached(path)
    if data is not None:
        return data
    data = client.get_all_pages(api_path, accept=accept)
    write_json(path, data)
    return data


def load_seed() -> list[dict[str, Any]]:
    return read_json(RAW / "all-title-matches.json")


def seed_sets(seed: list[dict[str, Any]]) -> tuple[set[int], set[int]]:
    issues: set[int] = set()
    prs: set[int] = set()
    for item in seed:
        n = int(item["number"])
        if "pull_request" in item:
            prs.add(n)
        else:
            issues.add(n)
    return issues, prs


def body_refs_issue(body: str | None, issue_numbers: set[int]) -> list[int]:
    if not body:
        return []
    refs = sorted({int(m.group(1)) for m in ISSUE_REF_RE.finditer(body) if int(m.group(1)) in issue_numbers})
    return refs


def timeline_crossrefs(timeline: list[dict[str, Any]], issue_number: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ev in timeline:
        source = ev.get("source") or {}
        src_issue = source.get("issue") or {}
        src_pr = src_issue.get("pull_request")
        if ev.get("event") == "cross-referenced" and src_pr and src_issue.get("number"):
            rows.append({
                "issue_number": issue_number,
                "pr_number": int(src_issue["number"]),
                "event": ev.get("event", ""),
                "created_at": ev.get("created_at", ""),
                "actor": ((ev.get("actor") or {}).get("login") or ""),
                "source_type": source.get("type", ""),
                "source_title": src_issue.get("title", ""),
                "source_url": src_issue.get("html_url", ""),
            })
    return rows


def summarize_text(value: str | None, max_len: int = 500) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()[:max_len]


def enrich(args: argparse.Namespace) -> dict[str, Any]:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    client = Client(token=token, max_requests=args.max_requests, min_remaining=args.min_remaining, wait=args.wait)
    seed = load_seed()
    seed_issues, seed_prs = seed_sets(seed)
    discovered_prs: set[int] = set()
    crossref_rows: list[dict[str, Any]] = []
    issue_rows: dict[int, dict[str, Any]] = {}
    pr_rows: dict[int, dict[str, Any]] = {}
    body_ref_rows: list[dict[str, Any]] = []

    print(f"seed: {len(seed_issues)} issues, {len(seed_prs)} PRs")

    try:
        for idx, issue_number in enumerate(sorted(seed_issues), start=1):
            issue_dir = RAW_ISSUES / str(issue_number)
            issue = fetch_cached(client, issue_dir / "issue.json", f"/repos/{REPO}/issues/{issue_number}")
            comments = fetch_pages_cached(client, issue_dir / "comments.json", f"/repos/{REPO}/issues/{issue_number}/comments")
            timeline = fetch_pages_cached(client, issue_dir / "timeline.json", f"/repos/{REPO}/issues/{issue_number}/timeline", accept=TIMELINE_ACCEPT)
            refs = timeline_crossrefs(timeline, issue_number)
            for row in refs:
                discovered_prs.add(row["pr_number"])
            crossref_rows.extend(refs)
            issue_rows[issue_number] = {
                "number": issue_number,
                "state": issue.get("state", ""),
                "title": issue.get("title", ""),
                "url": issue.get("html_url", ""),
                "created_at": issue.get("created_at", ""),
                "updated_at": issue.get("updated_at", ""),
                "closed_at": issue.get("closed_at", ""),
                "user": ((issue.get("user") or {}).get("login") or ""),
                "labels": ";".join(l.get("name", "") for l in issue.get("labels", [])),
                "comments_count": issue.get("comments", 0),
                "downloaded_comments": len(comments),
                "timeline_events": len(timeline),
                "crossref_pr_count": len({r["pr_number"] for r in refs}),
                "body_excerpt": summarize_text(issue.get("body")),
            }
            if idx % 10 == 0 or refs:
                print(f"issues {idx}/{len(seed_issues)}: #{issue_number}, refs={len(refs)}, discovered_prs={len(discovered_prs)}, requests={client.requests}")

        all_prs = set(seed_prs) | discovered_prs
        for idx, pr_number in enumerate(sorted(all_prs), start=1):
            pr_dir = RAW_PRS / str(pr_number)
            issue = fetch_cached(client, pr_dir / "issue.json", f"/repos/{REPO}/issues/{pr_number}")
            pr = fetch_cached(client, pr_dir / "pull.json", f"/repos/{REPO}/pulls/{pr_number}")
            files = fetch_pages_cached(client, pr_dir / "files.json", f"/repos/{REPO}/pulls/{pr_number}/files")
            reviews = fetch_pages_cached(client, pr_dir / "reviews.json", f"/repos/{REPO}/pulls/{pr_number}/reviews")
            review_comments = fetch_pages_cached(client, pr_dir / "review_comments.json", f"/repos/{REPO}/pulls/{pr_number}/comments")
            issue_comments = fetch_pages_cached(client, pr_dir / "issue_comments.json", f"/repos/{REPO}/issues/{pr_number}/comments")
            refs_in_body = body_refs_issue(issue.get("body"), seed_issues)
            for issue_number in refs_in_body:
                body_ref_rows.append({"pr_number": pr_number, "issue_number": issue_number, "source": "pr_body"})
            pr_rows[pr_number] = {
                "number": pr_number,
                "state": issue.get("state", ""),
                "title": issue.get("title", ""),
                "url": issue.get("html_url", ""),
                "created_at": issue.get("created_at", ""),
                "updated_at": issue.get("updated_at", ""),
                "closed_at": issue.get("closed_at", ""),
                "merged_at": pr.get("merged_at", ""),
                "user": ((issue.get("user") or {}).get("login") or ""),
                "labels": ";".join(l.get("name", "") for l in issue.get("labels", [])),
                "seed_title_match": pr_number in seed_prs,
                "discovered_from_issue_timeline": pr_number in discovered_prs,
                "referenced_seed_issues_in_body": ";".join(str(n) for n in refs_in_body),
                "base_ref": ((pr.get("base") or {}).get("ref") or ""),
                "head_ref": ((pr.get("head") or {}).get("ref") or ""),
                "merged": pr.get("merged", False),
                "changed_files": pr.get("changed_files", ""),
                "additions": pr.get("additions", ""),
                "deletions": pr.get("deletions", ""),
                "files_downloaded": len(files),
                "reviews_downloaded": len(reviews),
                "review_comments_downloaded": len(review_comments),
                "issue_comments_downloaded": len(issue_comments),
                "body_excerpt": summarize_text(issue.get("body")),
            }
            if idx % 10 == 0 or (pr_number in discovered_prs and pr_number not in seed_prs):
                print(f"prs {idx}/{len(all_prs)}: #{pr_number}, seed={pr_number in seed_prs}, discovered={pr_number in discovered_prs}, requests={client.requests}")
    except RateLimitStop as e:
        print(f"STOP: {e}", file=sys.stderr)

    # Rebuild normalized outputs from every raw file present, not just this run's in-memory rows.
    issue_rows, crossref_rows = rebuild_issue_outputs(seed_issues)
    all_prs = set(seed_prs) | {r["pr_number"] for r in crossref_rows}
    pr_rows, body_ref_rows = rebuild_pr_outputs(all_prs, seed_prs, seed_issues, {r["pr_number"] for r in crossref_rows})

    write_outputs(seed_issues, seed_prs, issue_rows, pr_rows, crossref_rows, body_ref_rows, client)
    candidate_numbers = (set(seed_prs) | {r["pr_number"] for r in crossref_rows})
    return {
        "seed_issues": len(seed_issues),
        "seed_prs": len(seed_prs),
        "issues_enriched": len(issue_rows),
        "candidate_pr_numbers": len(candidate_numbers),
        "candidate_prs_enriched": len(pr_rows),
        "timeline_crossrefs": len(crossref_rows),
        "body_refs": len(body_ref_rows),
        "new_prs_beyond_title_matches": len(candidate_numbers - seed_prs),
        "requests_this_run": client.requests,
        "rate_remaining": client.rate.get("x-ratelimit-remaining"),
        "rate_reset": client.rate.get("x-ratelimit-reset"),
    }


def rebuild_issue_outputs(seed_issues: set[int]) -> tuple[dict[int, dict[str, Any]], list[dict[str, Any]]]:
    issue_rows: dict[int, dict[str, Any]] = {}
    crossref_rows: list[dict[str, Any]] = []
    for issue_number in sorted(seed_issues):
        issue_dir = RAW_ISSUES / str(issue_number)
        issue_path = issue_dir / "issue.json"
        comments_path = issue_dir / "comments.json"
        timeline_path = issue_dir / "timeline.json"
        if not issue_path.exists():
            continue
        issue = read_json(issue_path)
        comments = read_json(comments_path) if comments_path.exists() else []
        timeline = read_json(timeline_path) if timeline_path.exists() else []
        refs = timeline_crossrefs(timeline, issue_number)
        crossref_rows.extend(refs)
        issue_rows[issue_number] = {
            "number": issue_number,
            "state": issue.get("state", ""),
            "title": issue.get("title", ""),
            "url": issue.get("html_url", ""),
            "created_at": issue.get("created_at", ""),
            "updated_at": issue.get("updated_at", ""),
            "closed_at": issue.get("closed_at", ""),
            "user": ((issue.get("user") or {}).get("login") or ""),
            "labels": ";".join(l.get("name", "") for l in issue.get("labels", [])),
            "comments_count": issue.get("comments", 0),
            "downloaded_comments": len(comments),
            "timeline_events": len(timeline),
            "crossref_pr_count": len({r["pr_number"] for r in refs}),
            "body_excerpt": summarize_text(issue.get("body")),
        }
    return issue_rows, crossref_rows


def rebuild_pr_outputs(all_prs: set[int], seed_prs: set[int], seed_issues: set[int], discovered_prs: set[int]) -> tuple[dict[int, dict[str, Any]], list[dict[str, Any]]]:
    pr_rows: dict[int, dict[str, Any]] = {}
    body_ref_rows: list[dict[str, Any]] = []
    for pr_number in sorted(all_prs):
        pr_dir = RAW_PRS / str(pr_number)
        issue_path = pr_dir / "issue.json"
        pull_path = pr_dir / "pull.json"
        if not issue_path.exists() or not pull_path.exists():
            continue
        issue = read_json(issue_path)
        pr = read_json(pull_path)
        files = read_json(pr_dir / "files.json") if (pr_dir / "files.json").exists() else []
        reviews = read_json(pr_dir / "reviews.json") if (pr_dir / "reviews.json").exists() else []
        review_comments = read_json(pr_dir / "review_comments.json") if (pr_dir / "review_comments.json").exists() else []
        issue_comments = read_json(pr_dir / "issue_comments.json") if (pr_dir / "issue_comments.json").exists() else []
        refs_in_body = body_refs_issue(issue.get("body"), seed_issues)
        for issue_number in refs_in_body:
            body_ref_rows.append({"pr_number": pr_number, "issue_number": issue_number, "source": "pr_body"})
        pr_rows[pr_number] = {
            "number": pr_number,
            "state": issue.get("state", ""),
            "title": issue.get("title", ""),
            "url": issue.get("html_url", ""),
            "created_at": issue.get("created_at", ""),
            "updated_at": issue.get("updated_at", ""),
            "closed_at": issue.get("closed_at", ""),
            "merged_at": pr.get("merged_at", ""),
            "user": ((issue.get("user") or {}).get("login") or ""),
            "labels": ";".join(l.get("name", "") for l in issue.get("labels", [])),
            "seed_title_match": pr_number in seed_prs,
            "discovered_from_issue_timeline": pr_number in discovered_prs,
            "referenced_seed_issues_in_body": ";".join(str(n) for n in refs_in_body),
            "base_ref": ((pr.get("base") or {}).get("ref") or ""),
            "head_ref": ((pr.get("head") or {}).get("ref") or ""),
            "merged": pr.get("merged", False),
            "changed_files": pr.get("changed_files", ""),
            "additions": pr.get("additions", ""),
            "deletions": pr.get("deletions", ""),
            "files_downloaded": len(files),
            "reviews_downloaded": len(reviews),
            "review_comments_downloaded": len(review_comments),
            "issue_comments_downloaded": len(issue_comments),
            "body_excerpt": summarize_text(issue.get("body")),
        }
    return pr_rows, body_ref_rows


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def write_outputs(seed_issues: set[int], seed_prs: set[int], issue_rows: dict[int, dict[str, Any]], pr_rows: dict[int, dict[str, Any]], crossref_rows: list[dict[str, Any]], body_ref_rows: list[dict[str, Any]], client: Client) -> None:
    issue_list = [issue_rows[n] for n in sorted(issue_rows)]
    pr_list = [pr_rows[n] for n in sorted(pr_rows)]
    crossref_rows = sorted(crossref_rows, key=lambda r: (r["issue_number"], r["pr_number"], r.get("created_at", "")))
    body_ref_rows = sorted(body_ref_rows, key=lambda r: (r["issue_number"], r["pr_number"]))

    discovered_prs = {r["pr_number"] for r in crossref_rows}
    candidate_numbers = [
        {
            "number": n,
            "seed_title_match": n in seed_prs,
            "discovered_from_issue_timeline": n in discovered_prs,
            "enriched": n in pr_rows,
        }
        for n in sorted(seed_prs | discovered_prs)
    ]

    write_json(PROCESSED / "candidate_issues.json", issue_list)
    write_json(PROCESSED / "candidate_prs.json", pr_list)
    write_json(PROCESSED / "candidate_pr_numbers.json", candidate_numbers)
    write_json(PROCESSED / "issue_pr_crossrefs.json", crossref_rows)
    write_json(PROCESSED / "pr_body_issue_refs.json", body_ref_rows)

    issue_fields = ["number", "state", "title", "url", "created_at", "updated_at", "closed_at", "user", "labels", "comments_count", "downloaded_comments", "timeline_events", "crossref_pr_count", "body_excerpt"]
    pr_fields = ["number", "state", "title", "url", "created_at", "updated_at", "closed_at", "merged_at", "user", "labels", "seed_title_match", "discovered_from_issue_timeline", "referenced_seed_issues_in_body", "base_ref", "head_ref", "merged", "changed_files", "additions", "deletions", "files_downloaded", "reviews_downloaded", "review_comments_downloaded", "issue_comments_downloaded", "body_excerpt"]
    candidate_number_fields = ["number", "seed_title_match", "discovered_from_issue_timeline", "enriched"]
    cross_fields = ["issue_number", "pr_number", "event", "created_at", "actor", "source_type", "source_title", "source_url"]
    body_fields = ["issue_number", "pr_number", "source"]

    write_csv(PROCESSED / "candidate_issues.csv", issue_list, issue_fields)
    write_csv(PROCESSED / "candidate_prs.csv", pr_list, pr_fields)
    write_csv(PROCESSED / "candidate_pr_numbers.csv", candidate_numbers, candidate_number_fields)
    write_csv(PROCESSED / "issue_pr_crossrefs.csv", crossref_rows, cross_fields)
    write_csv(PROCESSED / "pr_body_issue_refs.csv", body_ref_rows, body_fields)

    manifest = {
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "repo": REPO,
        "seed_issues": len(seed_issues),
        "seed_prs": len(seed_prs),
        "issues_enriched": len(issue_rows),
        "candidate_pr_numbers": len(candidate_numbers),
        "candidate_prs_enriched": len(pr_rows),
        "timeline_crossrefs": len(crossref_rows),
        "pr_body_issue_refs": len(body_ref_rows),
        "new_prs_beyond_title_matches": sum(1 for row in candidate_numbers if row["discovered_from_issue_timeline"] and not row["seed_title_match"]),
        "raw_layout": {
            "issues": "raw/issues/<number>/{issue,comments,timeline}.json",
            "prs": "raw/prs/<number>/{issue,pull,files,reviews,review_comments,issue_comments}.json",
        },
        "requests_this_run": client.requests,
        "rate_limit": client.rate,
    }
    write_json(RAW / "expanded-manifest.json", manifest)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--max-requests", type=int, default=None, help="Stop after this many network requests; cached reads do not count.")
    p.add_argument("--min-remaining", type=int, default=1, help="Stop or wait when GitHub core remaining reaches this count.")
    p.add_argument("--wait", action="store_true", help="Sleep through rate limits instead of stopping. Useful for authenticated long runs.")
    args = p.parse_args()
    result = enrich(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
