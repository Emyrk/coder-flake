# Coder CI flakes: what we found

A flake is a test or CI failure that fails nondeterministically, then often passes on rerun. This research looked at GitHub issues and PRs in [`coder/coder`](https://github.com/coder/coder) that mention test flakes, then grouped them by failure mode.

## Short version

Coder's flakes are not random. They cluster around a few repeat patterns:

| category | rows |
| --- | ---: |
| Networking, proxy, websocket | 105 |
| Workspace, agent, provisioner lifecycle | 102 |
| Concurrency and races | 74 |
| Database, transactions, migrations | 47 |
| Browser, e2e, Playwright | 47 |
| Timing and eventual consistency | 46 |

The main fix is not bigger timeouts. The main fix is better test structure:

1. Wait for real state, not time.
2. Isolate mutable state per test and subtest.
3. Use fakes or injected transports instead of real external systems.
4. Track flakes by signature so rerun-green failures do not disappear.
5. Quarantine noisy tests only with owner, reason, date, and expiry.

## Recommended first move

Start with workspace, agent, and provisioner lifecycle tests.

That bucket is large, central to Coder, and likely to produce reusable helper wins. Build shared helpers that wait for exact lifecycle milestones:

- workspace build created
- provisioner job started
- provisioner job completed or failed
- expected provisioner log line drained
- agent connected and ready
- workspace app route available

The helper should report the last observed state when it times out. That turns a flaky timeout into a useful failure.

## Why this matters

Repeated flakes burn CI minutes, hide real regressions, and train engineers to ignore red builds. Worse, a rerun that turns green deletes the evidence unless we record the signature.

The research shows recurring root causes and recurring fixes. That means we can treat flakes as a reliability program, not a pile of one-off bugs.

## Proposed rollout

1. Baseline and containment, 1 to 2 weeks
   - Add a flake issue template and category taxonomy.
   - Track normalized flake signatures.
   - Require quarantine metadata: issue, owner, category, date, retirement condition.

2. Deterministic helpers, 2 to 6 weeks
   - Harden lifecycle helpers for workspace, provisioner, agent, and log drain states.
   - Add deterministic time fixtures for scheduling and metrics tests.
   - Add isolated HTTP client and transport helpers.
   - Add websocket readiness and close-drain helpers.

3. Detection automation, 4 to 8 weeks
   - Add a targeted `go test -count` and `-race` workflow for labeled flakes.
   - Add nightly stress runs for high-risk packages.
   - Upload Playwright traces, screenshots, and locator state for browser flakes.

4. Enforcement, after signal stabilizes
   - Promote safe known-pattern checks to blocking.
   - Require verification commands in flake fix PRs.
   - Enforce quarantine expiry for high-value tests.

## Links

- [Full proposal](notes/proposed-solutions.md)
- [Common fixes by category](notes/common-solutions.md)
- [Category taxonomy](notes/category-taxonomy.md)
- [Categorized data](processed/categories.csv)
- [Crawler and raw data](README.md)

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
<summary>Category notes</summary>

Networking, proxy, websocket, 105 rows. Transport tests often observed distributed network state too early or assumed ideal delivery. Examples include websocket close races, DERP versus direct path assumptions, random port conflicts, DNS noise, and tunnel startup latency.

Workspace, agent, provisioner lifecycle, 102 rows. Tests often asserted before a workspace, provisioner job, agent, PTY, log stream, or template version reached the expected state.

Concurrency and races, 74 rows. Shared mutable state, goroutine cleanup, waitgroups, contexts, maps, and parallel subtests produced nondeterministic outcomes.

Database, transactions, migrations, 47 rows. Shared Postgres resources, cleanup gaps, socket leaks, transaction timing, migration behavior, and DB-backed async state amplified flakes.

Browser, e2e, Playwright, 47 rows. UI tests often asserted against transient state, ambiguous selectors, unflushed React state, browser dependency availability, or navigation before the page settled.

Timing and eventual consistency, 46 rows. Tests checked async state before convergence or compared wall-clock values too tightly.

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
