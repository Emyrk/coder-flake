# Coder CI flakes: wiki summary

A flake is a test or CI failure that fails nondeterministically, then often passes on rerun. We analyzed flake-related issues and PRs in [`coder/coder`](https://github.com/coder/coder), grouped them by failure mode, and looked for fixes that repeat.

## What we found

Coder flakes are not random. Most fall into a few recurring buckets.

| rank | category | references | common fix |
| ---: | --- | ---: | --- |
| 1 | [Networking, proxy, websocket](categories/networking-proxy-websocket.md) | 105 | Add explicit server-ready signals before clients connect. |
| 2 | [Workspace, agent, provisioner lifecycle](categories/workspace-agent-lifecycle.md) | 102 | Wait for exact lifecycle states: build created, provisioner job started, job complete, logs drained, agent ready, app route available. |
| 3 | [Concurrency and races](categories/concurrency-race.md) | 74 | Scope state per subtest. Copy maps and testcase structs before `t.Parallel()`. |
| 4 | [Database, transactions, migrations](categories/database-transactions-migrations.md) | 47 | Create isolated DB resources per test where practical. |
| 5 | [Browser, e2e, Playwright](categories/browser-e2e-playwright.md) | 47 | Use stable selectors and avoid broad text or role matches that can hit multiple elements. |
| 6 | [Timing and eventual consistency](categories/timing-eventual-consistency.md) | 46 | Inject clocks or pass explicit time values in scheduling, TTL, metrics, and status tests. |
| 7 | [Not a test flake: Nix flake or maintenance](categories/not-a-test-flake-nix-flake-or-maintenance.md) | 41 | Filter them out of test-flake dashboards. |
| 8 | [Platform or OS-specific CI behavior](categories/platform-os-specific-ci-behavior.md) | 31 | Record OS, CPU, memory, shell, and package parallelism in failure output. |
| 9 | [Unknown or needs manual read](categories/unknown-needs-manual-read.md) | 25 | Improve flake issue templates so reports include test name, package, job, platform, error signature, and rerun status. |
| 10 | [Resource exhaustion and timeouts](categories/resource-exhaustion-timeout.md) | 21 | Log runner CPU, memory, job name, package, and parallelism in failure output. |
| 11 | [Test isolation and order dependency](categories/test-isolation-order-dependency.md) | 20 | Generate unique users, orgs, workspace names, ports, paths, and DB rows per test. |
| 12 | [External service and dependency](categories/external-service-dependency.md) | 4 | Use fake servers or injected transports for CI tests. |

References means GitHub artifacts in the research corpus: one issue or one PR. This corpus has 563 references total. It is not a count of unique flaky tests.

## Quick and dirty

The repeated mistakes, sorted roughly by occurrence:

- Network tests assume the route, socket, websocket, DERP path, or proxy state is ready before it is.
- Workspace and agent tests assert before provisioners, agents, builds, PTYs, logs, or apps reach the expected lifecycle point.
- Parallel tests share state: maps, contexts, transports, users, deployments, ports, DB rows, or goroutines.
- DB-backed tests leak resources or depend on timing around transactions, migrations, cleanup, or Postgres runner behavior.
- Browser tests assert against transient UI state, ambiguous selectors, or navigation before the page settles.
- Time-based tests compare wall-clock values too tightly or call `time.Now()` around boundaries.
- CI jobs run platform-sensitive tests with the wrong assumptions about OS, CPU, memory, shell, browser, or Postgres behavior.
- Quarantine sometimes removes pain without recording owner, expiry, or retirement criteria.

## Recommended approach

Do not solve this as one giant flake cleanup. Treat it as a reliability program with category-specific fixes.

1. Track flakes by signature: test name, package, normalized error, category, job, platform, linked issue or PR.
2. Add an intake template with failure link, category, suspected owner, reproduction command, rerun status, first seen, and last seen.
3. Fix top buckets with shared helpers: networking readiness, lifecycle waits, concurrency isolation, DB resource isolation, browser trace artifacts, deterministic time.
4. Quarantine with discipline: issue link, owner, category, date, retirement condition, and default expiry.
5. Add targeted detection: `go test -count=N`, `-race` for race suspects, nightly stress for high-risk packages, and repeated browser specs with traces.

## First workstream to pilot

Pick one category and make it boring.

Best pilot: [workspace, agent, and provisioner lifecycle](categories/workspace-agent-lifecycle.md). It is the second largest bucket, core to Coder, and the helper work should reduce timing, DB-backed lifecycle, and resource flakes too.

This is not the only category. It is just the best first slice.

## Links

- [Full proposal](notes/proposed-solutions.md)
- [Common fixes by category](notes/common-solutions.md)
- [Category taxonomy](notes/category-taxonomy.md)
- [Categorized data](processed/categories.csv)
- [Raw data and crawler](README.md)

<details>
<summary>Dataset details</summary>

Seed search:

- `repo:coder/coder type:issue flake in:title`
- `repo:coder/coder type:issue flaky in:title`
- `repo:coder/coder type:pr flake in:title`
- `repo:coder/coder type:pr flaky in:title`

Expanded corpus:

- 219 seed flake issues enriched
- 344 candidate PRs enriched
- 11 PRs discovered beyond title matches via issue timeline cross references
- 14 timeline cross references
- 26 PR body references to seed issues
- 563 categorized references total

This is a flake candidate corpus, not every issue and PR in `coder/coder`.

</details>
