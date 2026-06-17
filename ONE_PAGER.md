# Coder CI flakes: one-page summary

A flake is a test or CI failure that fails nondeterministically, then often passes on rerun. We analyzed flake-related issues and PRs in [`coder/coder`](https://github.com/coder/coder), grouped them by failure mode, and looked for fixes that repeat.

## What we found

Coder flakes are not random. Most fall into a few recurring buckets:

| rank | category | rows | common fix |
| ---: | --- | ---: | --- |
| 1 | Networking, proxy, websocket | 105 | explicit readiness, route assertions, local fakes, close-drain helpers |
| 2 | Workspace, agent, provisioner lifecycle | 102 | wait for real lifecycle state, not sleeps |
| 3 | Concurrency and races | 74 | isolate subtests, join goroutines, avoid shared mutable state |
| 4 | Database, transactions, migrations | 47 | isolate DB resources, clean up sockets/DBs, reduce DB-heavy parallelism |
| 5 | Browser, e2e, Playwright | 47 | stable selectors, trace artifacts, wait for settled UI state |
| 6 | Timing and eventual consistency | 46 | deterministic clocks, explicit time params, condition polling |
| 7 | Platform or OS-specific CI behavior | 31 | platform helpers, runner-aware parallelism, better failure metadata |
| 8 | Resource exhaustion and timeouts | 21 | right-size parallelism, log runner resources, avoid blanket timeout bumps |
| 9 | Test isolation and order dependency | 20 | unique names, temp dirs, ports, contexts, and cleanup per test |

There were also 41 false positives about Nix `flake.nix` maintenance and 25 rows that need manual reading.

## Quick and dirty

The repeated mistakes, sorted by occurrence:

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

1. Track flakes by signature.
   - test name
   - package or spec file
   - normalized error message
   - category
   - job and platform
   - linked issue or PR

2. Add an intake template.
   - failure link
   - category
   - suspected owner area
   - reproduction command
   - whether rerun passed
   - first seen and last seen

3. Fix the top buckets with shared helpers.
   - networking: server-ready, route-selected, message-ack, close-drain helpers
   - lifecycle: workspace build, provisioner job, log drain, agent ready helpers
   - concurrency: goroutine join, per-subtest context, immutable testcase helpers
   - DB: isolated DB resources, cleanup checks, package-specific parallelism
   - browser: stable locator helpers and mandatory trace artifacts on failure
   - time: injected clocks and explicit time parameters

4. Quarantine with discipline.
   - issue link
   - owner
   - category
   - date
   - retirement condition
   - default expiry, 30 days

5. Add targeted detection, not blanket reruns.
   - `go test -count=N` for labeled flakes
   - `-race` for race-suspect packages
   - nightly stress for high-risk packages
   - repeated Playwright/Jest specs with trace uploads

## First workstream to pilot

Pick one category and make it boring.

Best pilot: workspace, agent, and provisioner lifecycle. It is the second largest bucket, core to Coder, and the helper work should reduce timing, DB-backed lifecycle, and resource flakes too.

Pilot output:

- lifecycle wait helpers for build, provisioner, logs, agent ready, and app route state
- timeout errors that print the last observed state
- 3 to 5 existing flaky tests migrated to the helpers
- a short pattern doc showing when to use the helpers

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
- 563 categorized rows total

This is a flake candidate corpus, not every issue and PR in `coder/coder`.

</details>

<details>
<summary>Known flake smells to review for</summary>

Blocking smells:

- `time.Sleep` used for synchronization
- hardcoded ports
- fixed user, org, or workspace names in parallel tests
- `http.DefaultTransport` in parallel network/auth tests
- assertions before async writes or lifecycle completion
- `t.Fatal`, `require.*`, or `assert.*` from non-test goroutines
- real OpenAI, DNS, Docker, or external service calls in CI tests

Warning smells:

- shared mutable maps in testcase structs
- multiple `time.Now()` calls around boundary assertions
- teardown that cancels context before spawned goroutines finish
- platform-specific behavior without a platform helper or skip reason
- widened timeout without last-observed-state logging

</details>
