#!/usr/bin/env python3
"""Categorize coder/coder flake issues and PRs by failure mode.

This is intentionally heuristic. The source corpus is GitHub issue/PR metadata,
not normalized test result records. Keep the evidence column short enough for a
human to audit the category choice without opening the raw JSON for every row.
"""

from __future__ import annotations

import csv
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "processed"
RAW = ROOT / "raw"
NOTES = ROOT / "notes"

CATEGORY_RULES: list[tuple[str, list[str]]] = [
    (
        "platform/os-specific CI behavior",
        [
            r"\bwindows\b",
            r"windows-2022",
            r"\bmacos\b",
            r"\bosx\b",
            r"\bdarwin\b",
            r"zsh killed",
            r"aarch64",
            r"arm64",
            r"linux host",
        ],
    ),
    (
        "browser/e2e/playwright",
        [
            r"playwright",
            r"\be2e\b",
            r"browser",
            r"chromatic",
            r"storybook",
            r"locator",
            r"page\.",
            r"workspacepage",
            r"puppeteer",
            r"jest",
            r"vitest",
            r"frontend",
            r"testui",
            r"codemirror",
            r"visual",
            r"starter template",
        ],
    ),
    (
        "database/transactions/migrations",
        [
            r"postgres",
            r"postgresql",
            r"\bpsql\b",
            r"\bsql\b",
            r"database",
            r"\bdb\b",
            r"migration",
            r"transaction",
            r"create database",
            r"test database",
            r"serverdbcrypt",
        ],
    ),
    (
        "concurrency/race",
        [
            r"data race",
            r"race detected",
            r"race condition",
            r"\brace\b",
            r"deadlock",
            r"goroutine",
            r"mutex",
            r"concurrent",
            r"\block\b",
            r"poll race",
            r"leak",
            r"context\.cancel",
            r"context canceled",
            r"ctx cancelled",
            r"contextcancel",
            r"closed channel",
            r"signal wake",
            r"localsub",
            r"nats",
        ],
    ),
    (
        "networking/proxy/websocket",
        [
            r"websocket",
            r"\bws\b",
            r"wsconn",
            r"proxy",
            r"tunnel",
            r"tailnet",
            r"derp",
            r"wireguard",
            r"webrtc",
            r"\bice\b",
            r"\bturn\b",
            r"udp",
            r"tcp",
            r"portforward",
            r"port forward",
            r"\bssh\b",
            r"testssh",
            r"gitssh",
            r"\btls\b",
            r"x509",
            r"certificate",
            r"netconn",
            r"peer",
            r"socket",
            r"speedtest",
            r"port collision",
            r"listen .*address already in use",
            r"listener",
            r"network",
            r"malformed http status",
            r"transport connection",
        ],
    ),
    (
        "workspace/agent lifecycle",
        [
            r"workspace agent",
            r"workspaceagent",
            r"agent/session",
            r"sessiontty",
            r"reconnectingpty",
            r"pty",
            r"provisionerd",
            r"provisioner",
            r"workspacebuild",
            r"workspace app",
            r"workspaceapplication",
            r"template version",
            r"templateversion",
            r"build log",
            r"job log",
            r"agent lifecycle",
            r"reconnect",
            r"agentssh",
            r"agentapi",
            r"agentexec",
            r"agentcontainers",
            r"portabledesktop",
            r"workspace ttl",
            r"autobuild",
            r"dormancy",
            r"inactive stopped workspace",
        ],
    ),
    (
        "external service/dependency",
        [
            r"datadog",
            r"yarn",
            r"npm",
            r"node_modules",
            r"markdown-link",
            r"docker-practice",
            r"setup-docker",
            r"aws",
            r"github actions",
            r"external",
            r"dependency",
            r"registry",
            r"apt",
            r"homebrew",
            r"google cdn",
            r"google-chrome",
        ],
    ),
    (
        "resource exhaustion/timeout",
        [
            r"timeout",
            r"timed out",
            r"deadline exceeded",
            r"exceeded timeout",
            r"slow ci",
            r"oom",
            r"out of memory",
            r"\bcpu\b",
            r"memory",
            r"too long",
            r"buffer (?:full|filling)",
            r"resource exhausted",
            r"context deadline",
            r"loadtest",
            r"forcecancelinterval",
        ],
    ),
    (
        "test isolation/order dependency",
        [
            r"tempdir",
            r"cleanup",
            r"directory not empty",
            r"not clean",
            r"cache",
            r"same timestamp",
            r"already exists",
            r"\border\b",
            r"parallel tests",
            r"port-reuse",
            r"reused?",
            r"isolation",
            r"shared state",
            r"residual",
            r"colli(?:de|sion)",
            r"unique",
            r"random",
            r"generated password length",
            r"boundary test",
            r"duplicate",
        ],
    ),
    (
        "timing/eventual consistency",
        [
            r"eventually",
            r"eventual",
            r"\bwait",
            r"poll",
            r"retry",
            r"try again",
            r"sleep",
            r"ticker",
            r"backoff",
            r"not ready",
            r"not all logs",
            r"status code 404",
            r"previous template version",
            r"visibility",
            r"propagat",
            r"delay",
            r"duration",
            r"\bttl\b",
            r"time\.now",
            r"deterministic time",
            r"temporal assertion",
            r"timestamp",
            r"activitybump",
            r"activity bump",
            r"insights",
            r"metrics",
            r"prometheus",
            r"lastmodelconfigid",
            r"desc cache",
            r"aggregation",
            r"condition never satisfied",
        ],
    ),
]

NIX_OR_MAINTENANCE_PATTERNS = [
    r"flake\.nix",
    r"nix flake",
    r"update-flake",
    r"update flake",
    r"add sapling to the nix flake",
    r"pin sqlc",
    r"flake\.lock",
    r"nix dogfood",
    r"buildnixshellimage",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def load_json(path: Path, default: Any) -> Any:
    try:
        with path.open() as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def raw_issue_text(number: str) -> str:
    base = RAW / "issues" / number
    parts: list[str] = []
    issue = load_json(base / "issue.json", {})
    for key in ("title", "body"):
        if issue.get(key):
            parts.append(str(issue[key]))
    for comment in load_json(base / "comments.json", [])[:8]:
        if comment.get("body"):
            parts.append(str(comment["body"]))
    return "\n".join(parts)


def raw_pr_text(number: str) -> tuple[str, str]:
    base = RAW / "prs" / number
    parts: list[str] = []
    title_body_parts: list[str] = []
    for filename in ("pull.json", "issue.json"):
        obj = load_json(base / filename, {})
        for key in ("title", "body"):
            if obj.get(key):
                value = str(obj[key])
                title_body_parts.append(value)
                parts.append(value)
    for file_obj in load_json(base / "files.json", [])[:30]:
        if file_obj.get("filename"):
            parts.append(str(file_obj["filename"]))
    for comment in load_json(base / "issue_comments.json", [])[:6]:
        if comment.get("body"):
            parts.append(str(comment["body"]))
    return "\n".join(parts), "\n".join(title_body_parts)


def classify(text: str, title_body_text: str) -> tuple[str, list[str]]:
    title_body_lower = title_body_text.lower()
    nix_hits = [pat for pat in NIX_OR_MAINTENANCE_PATTERNS if re.search(pat, title_body_lower)]
    if nix_hits:
        return "not-a-test-flake/nix-flake-or-maintenance", nix_hits

    lowered = text.lower()
    scores: list[tuple[int, int, str, list[str]]] = []
    for index, (category, patterns) in enumerate(CATEGORY_RULES):
        hits = [pattern for pattern in patterns if re.search(pattern, lowered)]
        if hits:
            scores.append((len(hits), -index, category, hits))
    if not scores:
        return "unknown/needs manual read", []
    scores.sort(reverse=True)
    _, _, category, hits = scores[0]
    return category, hits[:5]


def excerpt(text: str, hits: list[str], limit: int = 420) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return ""
    lowered = clean.lower()
    positions: list[int] = []
    for pattern in hits:
        match = re.search(pattern, lowered)
        if match:
            positions.append(match.start())
    start = max(0, (min(positions) if positions else 0) - 80)
    result = clean[start : start + limit]
    if start:
        result = "…" + result
    if len(clean) > start + limit:
        result += "…"
    return result.replace("\r", " ")


def status_for_issue(row: dict[str, str], linked_prs: list[str], pr_by_number: dict[str, dict[str, str]]) -> str:
    status = row["state"]
    if linked_prs:
        merged = [number for number in linked_prs if pr_by_number.get(number, {}).get("merged") == "True"]
        status += "; linked_fix_merged" if merged else "; linked_fix_unmerged_or_unknown"
    return status


def status_for_pr(row: dict[str, str]) -> str:
    status = row["state"]
    if row.get("merged") == "True":
        status += "; merged"
    elif row.get("merged") == "False":
        status += "; not_merged"
    return status


def representative_examples(rows: list[dict[str, str]], category: str, limit: int = 4) -> list[dict[str, str]]:
    examples = [row for row in rows if row["category"] == category and row["evidence"]]
    # Prefer issues and then rows with linked fixes, because they are easier to audit.
    examples.sort(key=lambda row: (row["kind"] != "issue", not row["linked_fix_prs"], int(row["number"])))
    return examples[:limit]


def build_taxonomy(rows: list[dict[str, str]]) -> str:
    counts = Counter(row["category"] for row in rows)
    issue_counts = Counter(row["category"] for row in rows if row["kind"] == "issue")
    pr_counts = Counter(row["category"] for row in rows if row["kind"] == "PR")

    category_descriptions = {
        "browser/e2e/playwright": "Browser-driven or frontend integration tests, including Playwright, Storybook, page/locator waits, and JS UI harness failures.",
        "concurrency/race": "Shared-memory, goroutine, locking, cancellation, pubsub, or data-race failures where interleavings change the result.",
        "database/transactions/migrations": "Postgres, SQL, migrations, database cleanup, transaction semantics, or DB-backed tests.",
        "external service/dependency": "Failures rooted in outside services or dependency managers such as Yarn, Datadog, Docker setup, AWS, registries, or CDN availability.",
        "networking/proxy/websocket": "Transport-layer flakes: SSH, websockets, tunnels, tailnet/DERP/WireGuard/WebRTC, sockets, ports, TLS, x509, and proxy behavior.",
        "not-a-test-flake/nix-flake-or-maintenance": "Search false positives or maintenance PRs about Nix flakes, flake.lock, or update-flake automation rather than nondeterministic tests.",
        "platform/os-specific CI behavior": "Behavior that only reproduces on a particular CI OS or architecture, especially Windows, macOS, Darwin, zsh, ARM64, or host shell differences.",
        "resource exhaustion/timeout": "Slow or overloaded runs, deadline/context timeouts, buffer exhaustion, OOM, CPU/memory pressure, and explicit test timeout adjustments.",
        "test isolation/order dependency": "State leaking across tests: temp dirs, cache, duplicate names, timestamp collisions, random ordering, reused ports, cleanup gaps, or parallel-test interference.",
        "timing/eventual consistency": "Async systems observed too early or with brittle temporal assertions: polling, retry, sleep, TTL, metrics/insights aggregation, log visibility, and deterministic-time fixes.",
        "unknown/needs manual read": "Not enough signal in the downloaded metadata to assign a reliable failure mode without reading the linked run, code, or full discussion.",
        "workspace/agent lifecycle": "Coder workspace, provisioner, agent, PTY, reconnect, template-version, workspace build/log, desktop, container, or agent API lifecycle flakes.",
    }

    lines: list[str] = []
    lines.append("# Coder flake failure-mode taxonomy")
    lines.append("")
    lines.append("Generated from `processed/candidate_issues.csv`, `processed/candidate_prs.csv`, and the raw GitHub JSON under `raw/`.")
    lines.append("")
    lines.append(f"Corpus categorized: {len(rows)} rows, {sum(row['kind'] == 'issue' for row in rows)} issues and {sum(row['kind'] == 'PR' for row in rows)} PRs.")
    lines.append("")
    lines.append("The categorization is heuristic. The `evidence` column in `processed/categories.csv` is the audit trail for each row.")
    lines.append("")
    lines.append("## Category counts")
    lines.append("")
    lines.append("| category | total | issues | PRs |")
    lines.append("| --- | ---: | ---: | ---: |")
    for category, total in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {category} | {total} | {issue_counts[category]} | {pr_counts[category]} |")
    lines.append("")
    lines.append("## Taxonomy")
    lines.append("")
    for category, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"### {category}")
        lines.append("")
        lines.append(category_descriptions.get(category, "No description."))
        lines.append("")
        lines.append("Representative examples:")
        for row in representative_examples(rows, category):
            linked = f", linked fixes {row['linked_fix_prs']}" if row["linked_fix_prs"] else ""
            evidence = row["evidence"].replace("|", "\\|")
            lines.append(f"- {row['kind']} #{row['number']}: {row['title']} ({row['status']}{linked}). Evidence: {evidence}")
        if not representative_examples(rows, category):
            lines.append("- No compact evidence excerpt available in the downloaded metadata.")
        lines.append("")
    lines.append("## Notes on interpretation")
    lines.append("")
    lines.append("- Rows are categorized independently. A linked issue and fix PR can land in different categories if the PR title/body exposes a more specific cause than the issue report.")
    lines.append("- `not-a-test-flake/nix-flake-or-maintenance` is intentional. The seed search matched `flake.nix` and update-flake maintenance work, which is not nondeterministic test flakiness.")
    lines.append("- `unknown/needs manual read` means the local metadata did not contain enough cause text. It does not mean the failure is unknowable.")
    lines.append("- Categories are failure-mode oriented, not component ownership. For example, a workspace agent websocket failure should be networking if the transport is the root signal, and workspace/agent lifecycle if the lifecycle sequencing is the root signal.")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    issues = read_csv(PROCESSED / "candidate_issues.csv")
    prs = read_csv(PROCESSED / "candidate_prs.csv")
    pr_by_number = {row["number"]: row for row in prs}

    issue_to_prs: dict[str, set[str]] = defaultdict(set)
    for filename in ("issue_pr_crossrefs.csv", "pr_body_issue_refs.csv"):
        for row in read_csv(PROCESSED / filename):
            issue_to_prs[row["issue_number"]].add(row["pr_number"])

    rows: list[dict[str, str]] = []

    for issue in issues:
        number = issue["number"]
        linked_prs = sorted(issue_to_prs[number], key=int)
        linked_context: list[str] = []
        for pr_number in linked_prs:
            pr = pr_by_number.get(pr_number)
            if pr:
                linked_context.append(f"PR #{pr_number}: {pr['title']} {pr.get('body_excerpt', '')}")
        title_body = "\n".join([issue["title"], issue.get("body_excerpt", ""), raw_issue_text(number)])
        full_text = title_body + "\n" + "\n".join(linked_context)
        category, hits = classify(full_text, title_body)
        rows.append(
            {
                "number": number,
                "kind": "issue",
                "title": issue["title"],
                "category": category,
                "evidence": excerpt(full_text, hits),
                "linked_fix_prs": ";".join(f"#{pr_number}" for pr_number in linked_prs),
                "status": status_for_issue(issue, linked_prs, pr_by_number),
            }
        )

    for pr in prs:
        number = pr["number"]
        full_text, title_body = raw_pr_text(number)
        if not full_text:
            full_text = "\n".join([pr["title"], pr.get("body_excerpt", "")])
            title_body = full_text
        else:
            full_text = "\n".join([pr["title"], pr.get("body_excerpt", ""), full_text])
            title_body = "\n".join([pr["title"], pr.get("body_excerpt", ""), title_body])
        category, hits = classify(full_text, title_body)
        rows.append(
            {
                "number": number,
                "kind": "PR",
                "title": pr["title"],
                "category": category,
                "evidence": excerpt(full_text, hits),
                "linked_fix_prs": f"#{number}" if pr.get("merged") == "True" and category != "not-a-test-flake/nix-flake-or-maintenance" else "",
                "status": status_for_pr(pr),
            }
        )

    PROCESSED.mkdir(exist_ok=True)
    NOTES.mkdir(exist_ok=True)
    out_csv = PROCESSED / "categories.csv"
    with out_csv.open("w", newline="") as f:
        fieldnames = ["number", "kind", "title", "category", "evidence", "linked_fix_prs", "status"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    taxonomy = build_taxonomy(rows)
    (NOTES / "category-taxonomy.md").write_text(taxonomy)

    counts = Counter(row["category"] for row in rows)
    print(f"wrote {out_csv} ({len(rows)} rows)")
    print(f"wrote {NOTES / 'category-taxonomy.md'}")
    for category, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        print(f"{count:3d} {category}")


if __name__ == "__main__":
    main()
