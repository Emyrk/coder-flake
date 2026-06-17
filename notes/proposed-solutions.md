# Proposed anti-flake strategy for coder/coder

Source inputs:

- `notes/common-solutions.md`
- `processed/categories.csv`

Corpus summary: 563 categorized rows: 344 PRs and 219 issues. The highest-volume categories are networking/proxy/websocket (105), workspace/agent lifecycle (102), concurrency/race (74), database/transactions/migrations (47), browser/e2e/playwright (47), and timing/eventual consistency (46). The proposal below treats the 41 `not-a-test-flake/nix-flake-or-maintenance` rows as CI maintenance signal, not nondeterministic test-flake signal.

## Executive proposal

Coder should treat flakes as a product-quality program, not a whack-a-mole CI chore. The corpus shows repeated root causes, repeated fixes, and repeated containment patterns. The highest-leverage strategy is:

1. Make the test harness deterministic around lifecycle, time, concurrency, and external systems.
2. Add a first-class flake detection workflow that reruns targeted tests under stress, race detector, and randomized order.
3. Quarantine noisy tests quickly, but require ownership, expiry, and a path to repair.
4. Measure improvement by recurrence, time-to-diagnosis, quarantine aging, rerun rate, and known-pattern prevalence.

The main anti-pattern to avoid: blindly widening timeouts. It sometimes helps, but in this corpus it often hides missing synchronization, leaked state, undersized CI runners, or real product races.

## Principles

### 1. Wait for state, not time

Most major categories include tests observing asynchronous state too early: workspace builds, agents, provisioner logs, websocket readers, metrics, UI navigation, and notification loops. The default fix should be an observable state transition with a helper, not `time.Sleep` or a larger deadline.

Examples from the corpus:

- Workspace lifecycle fixes waited for provisioner jobs, build state, agent startup, or log drains.
- Timing fixes passed explicit time values, used deterministic clocks, or polled for the actual condition.
- Browser fixes waited for stable UI state and specific selectors instead of transient URLs or immediate DOM shape.

### 2. Scope mutable state per subtest

Parallel tests need isolated contexts, users, deployments, transports, temp paths, mock clocks, maps, fake providers, and DB rows. Several historical flakes came from one subtest poisoning siblings through shared context cancellation, shared deployments, shared maps, or shared HTTP transports.

### 3. Prefer fakes and injected transports over real external systems

Network, OpenAI, DNS, Docker, browser dependencies, and shared default transports all show up as flake amplifiers. Unit and integration tests should use local fake servers, injected `http.RoundTripper`s, deterministic DNS/DERP behavior, and hermetic dependency provisioning wherever possible.

### 4. Treat platform and resource flakes as first-class signals

Windows, macOS, ARM64, zsh, slow runners, 4-vCPU jobs, PTY exhaustion, and Postgres runner behavior recur. A failing platform job is not automatically a product bug, but it is still a contract the test suite is making with CI. Fix the helper, narrow the platform matrix for that test, or lower parallelism.

### 5. Quarantine is containment, not closure

The corpus includes many skips and removals. Some were appropriate. The difference between useful quarantine and CI theater is ownership plus expiry. A skipped flake should name the issue, owner area, reason, date, and retirement condition.

## High-leverage engineering fixes

### A. Build lifecycle-aware test helpers for workspace, agent, and provisioner flows

Target categories:

- `workspace/agent lifecycle`, 102 rows
- `timing/eventual consistency`, 46 rows
- overlaps with `database/transactions/migrations` and `test isolation/order dependency`

Proposal:

Create or harden shared helpers that wait for exact lifecycle milestones:

- workspace build created
- provisioner job started
- provisioner job completed or failed
- expected provisioner log line drained
- agent connected and ready
- agent metadata collected
- workspace app route available
- audit log event persisted
- notification or metrics write observed

Rules for these helpers:

- They poll a specific API or DB condition.
- They accept a context from the test and annotate timeout errors with the last observed state.
- They avoid sleeping blindly.
- They register cleanup that waits for background goroutines or server shutdown where relevant.
- They are easy enough that test authors choose them over local ad hoc loops.

Expected payoff:

This attacks the second-largest category directly and reduces misleading timeout symptoms in several other categories.

### B. Standardize deterministic time

Target categories:

- `timing/eventual consistency`, 46 rows
- `database/transactions/migrations`, especially timestamp precision
- `platform/os-specific CI behavior`, especially Windows and macOS time behavior

Proposal:

Adopt a stronger rule: tests that assert scheduling, TTLs, autostart/autostop, metrics windows, user status, template activity, or time ranges must use one of:

- injected clock
- explicit time parameter
- frozen clock fixture
- widened range only when the product genuinely measures elapsed wall-clock time

Add review guidance: two independent `time.Now()` calls around a boundary are a flake smell. So are assertions that expect exact timestamp equality after database round trips.

Expected payoff:

This converts time bugs from probabilistic to deterministic. It also reduces OS-specific failures caused by clock precision or slow CI.

### C. Isolate HTTP clients, transports, and external dependencies per test

Target categories:

- `networking/proxy/websocket`, 105 rows
- `external service/dependency`, 4 rows but high cost
- `test isolation/order dependency`, 20 rows

Proposal:

Make shared-default usage suspicious in tests:

- avoid `http.DefaultClient` and `http.DefaultTransport` in parallel tests
- provide `coderdtest.NewHTTPClient(t)` or similar helper that owns its transport
- inject failing transports for error-path tests instead of closing servers and hoping for a specific error
- use fake local servers for OpenAI, DNS, devtunnel, auth token validation, and DERP-ish behavior where product semantics allow it
- provide one helper for "network must fail with this error" to prevent each test from inventing its own race

Expected payoff:

This addresses the largest category's test-harness side and prevents sibling tests from closing idle connections or mutating global transport state.

### D. Make websocket and network lifecycle edges explicit

Target categories:

- `networking/proxy/websocket`, 105 rows
- `concurrency/race`, 74 rows
- `resource exhaustion/timeout`, 21 rows

Proposal:

Add helper patterns for network tests:

- explicit server-ready signal before clients connect
- explicit reader-drained signal before close
- explicit ping or message acknowledgment when asserting bidirectional behavior
- retry only for lossy exchanges where retry is part of the production contract
- `:0` dynamic ports and listener-owned address discovery
- deterministic routing mode for tests that need DERP versus direct path

For tailnet, DERP, proxy, and websocket tests, require failure output to include connection state, selected route, server readiness, close reason, and last message observed.

Expected payoff:

Network flakes were the largest bucket. The goal is not to make network tests slower. It is to stop asserting before the network path being tested is actually in the requested state.

### E. Add concurrency guardrails to test helpers

Target categories:

- `concurrency/race`, 74 rows
- `workspace/agent lifecycle`, 102 rows
- `database/transactions/migrations`, 47 rows

Proposal:

Build and document helpers for common Coder race shapes:

- `StartWithWaiter` style command helpers that guarantee process completion before cleanup
- goroutine group helpers that join before `t.Cleanup` cancels contexts
- per-subtest context helpers that prevent one timeout from poisoning sibling subtests
- map-copy or immutable testcase helpers for parallel subtests
- test logging helpers that call `t.Helper()` and never call `t.Fatal` from non-test goroutines

Also add review checks for:

- `t.Fatal`, `require.*`, or `assert.*` inside goroutines
- shared maps or structs mutated by `t.Parallel()` subtests
- `defer cancel()` while background work is still using the context
- waitgroup `Add` racing with close or wait

Expected payoff:

This targets explicit race-detector failures and the common `Fail in goroutine after Test... has completed` shape.

### F. Right-size CI parallelism by job and package

Target categories:

- `resource exhaustion/timeout`, 21 rows
- `platform/os-specific CI behavior`, 31 rows
- `database/transactions/migrations`, 47 rows

Proposal:

Keep the recent pattern of tuning `flake-go` parallelism for actual runner capacity, but make it systematic:

- Record runner CPU and memory in flake workflow output.
- Compute worst-case package and subtest fanout for high-cost jobs.
- Cap Postgres, PTY, browser, and network-heavy package parallelism separately from pure unit tests.
- Run lower parallelism on Windows and other known fragile platforms.
- Add a CI note when a job uses a constrained profile so failures are interpreted correctly.

Expected payoff:

This prevents resource starvation from masquerading as product nondeterminism. It should reduce timeout noise without globally slowing the full suite.

## Process and tooling improvements

### 1. Create a flake intake template and taxonomy

Every new flake issue should capture:

- failing package and test name
- job, OS, runner class, CPU count if visible
- failure mode category from the taxonomy
- first seen date
- last seen date
- reproduction command
- whether rerun passed
- suspected owner area
- whether the failure is product race, test harness, CI resource, external dependency, or unknown

Use the categories already present in `processed/categories.csv` as the initial taxonomy:

- networking/proxy/websocket
- workspace/agent lifecycle
- concurrency/race
- database/transactions/migrations
- browser/e2e/playwright
- timing/eventual consistency
- platform/os-specific CI behavior
- resource exhaustion/timeout
- test isolation/order dependency
- external service/dependency
- unknown/needs manual read

Keep `not-a-test-flake/nix-flake-or-maintenance` separate so CI maintenance work does not distort test-flake metrics.

### 2. Add a review checklist for flaky-test patterns

Add this to PR review guidance or a lightweight CI lint where grep-able:

Blocking smells:

- `time.Sleep` used for synchronization
- hardcoded ports
- fixed user/org/workspace names in parallel tests
- `http.DefaultTransport` in parallel external-auth or server-close tests
- test assertions before async write or lifecycle completion
- test fatal/assertion from a non-test goroutine
- real OpenAI/DNS/external service calls in CI integration tests

Warning smells:

- shared mutable maps in testcase structs
- multiple `time.Now()` calls around boundary assertions
- teardown that cancels context before spawned goroutines finish
- platform-specific behavior without platform-specific helper or skip reason
- widened timeout without last-observed-state logging

### 3. Make flake fix PRs self-describing

A flake fix PR should state which repair class it uses:

- deterministic wait
- isolation
- fake/injected dependency
- race fix
- platform helper
- resource-budget change
- quarantine
- instrumentation only

Require the PR body to include the reproduction or verification command when available, for example:

- `go test -race -count=1000 ./coderd/... -run TestName`
- `gotestsum --rerun-fails --packages=... -- -count=100`
- Playwright repeat command for the affected spec

The corpus shows useful examples where PRs documented high-count or race-detector repros. Make that normal.

### 4. Maintain a known-pattern registry

Create a repo-local document or generated page for known Coder flake patterns. Seed it from the current research:

- CLI expecter without waiter
- time.Sleep synchronization
- hardcoded ports
- hardcoded names in parallel tests
- map iteration/order assertions
- async DB write read too early
- unclosed response bodies
- leaked goroutines
- shared `http.DefaultTransport`
- test contexts shared across subtests
- transient UI redirect assertions
- platform timestamp precision assertions

Use it for:

- review checklist
- flake triage
- automated grep/lint candidates
- onboarding test authors

### 5. Improve failure artifacts

For high-flake areas, failure output should include enough state to diagnose without rerunning blindly:

- workspace build state and provisioner job state
- last provisioner log line and whether log stream closed cleanly
- agent connection state and last heartbeat/metadata timestamp
- websocket route, close reason, last received message
- selected DERP/direct path when relevant
- database row IDs and timestamps for async assertions
- Playwright trace, screenshot, URL, and locator state
- runner OS, CPU, memory, and package parallelism

The goal is to reduce `unknown/needs manual read` and shorten time-to-diagnosis.

## Detection and quarantine strategy

### A. Detection workflows

Use three workflows, each with a distinct job.

#### 1. Targeted flake detector

Trigger:

- manually from a flake issue or PR label
- nightly against recently changed packages
- automatically when a test fails then passes on rerun

Behavior:

- runs the named test with `-count=N`
- enables `-race` for race-suspect packages
- randomizes test order where supported
- records per-attempt logs
- uploads summarized failure signatures

Use this for Go unit and integration tests.

#### 2. High-risk package stress suite

Trigger:

- nightly
- before release branches

Packages:

- networking, tailnet, proxy, websocket, DERP/devtunnel
- workspace lifecycle and provisioner packages
- Postgres-heavy packages
- browser/e2e specs with recent flakes

Behavior:

- runs with realistic but bounded parallelism
- runs a second profile with lower parallelism for resource-sensitive jobs
- captures runner metrics
- reports only new or recurrent signatures, not a wall of green logs

#### 3. Frontend/browser repeat suite

Trigger:

- nightly
- label for frontend flake suspect PRs

Behavior:

- repeats affected Playwright or Jest specs
- always uploads trace/screenshot/video on failure
- groups failures by locator, URL, and error signature

### B. Flake signature tracking

Track each flake by signature, not just issue number:

- normalized test name
- package/spec file
- primary error message
- stack top or failing assertion line
- category
- platform/job
- linked issue or PR

This distinguishes one noisy test with many repeats from many unrelated failures. It also allows metrics like recurrence after fix.

### C. Quarantine policy

Quarantine should be fast, explicit, and reversible.

Allowed reasons:

- failure blocks unrelated merges repeatedly
- external service dependency cannot be made hermetic immediately
- platform-specific behavior needs a dedicated helper
- product race is real but too risky to fix in the current PR

Required metadata in skip/TODO:

- issue link
- owner area or team
- category
- date quarantined
- retirement condition
- whether coverage is replaced elsewhere

Expiry:

- default 30 days
- 7 days for high-value product coverage
- no expiry only for explicitly unsupported platform behavior

Quarantine dashboard:

- total quarantined tests
- age buckets
- owner area
- category
- tests past expiry
- tests removed versus repaired

### D. Rerun policy

Reruns should classify flakes, not hide them.

- If a job passes on rerun, create or update a flake signature entry.
- If the same signature appears twice in a rolling window, require triage.
- If it appears on a release-blocking branch, quarantine or fix before continuing.
- Do not treat `rerun green` as success for reliability metrics.

## Measuring improvement

Track leading and lagging indicators.

### Lagging indicators

- Flaky failure rate per 100 CI runs.
- Unique flake signatures per week.
- Recurrent flake signatures after a merged fix.
- Median time from first seen to triaged.
- Median time from triaged to fixed or quarantined.
- Number of blocked PRs caused by known flaky signatures.
- Rerun rate and rerun minutes consumed.

### Leading indicators

- Percentage of flake fix PRs with a category and verification command.
- Percentage of new flake issues with complete intake fields.
- Count of quarantined tests past expiry.
- Count of tests using known risky patterns, for grep-able patterns.
- Number of high-risk packages covered by nightly stress workflows.
- Percentage of browser failures with trace artifacts.
- Percentage of lifecycle timeout failures with last-observed-state logs.

### Category-specific targets

Suggested first-quarter goals:

- Reduce new `workspace/agent lifecycle` and `timing/eventual consistency` signatures by 30 percent through lifecycle helpers and deterministic time.
- Reduce `networking/proxy/websocket` recurrence by 25 percent through explicit route/readiness/close instrumentation and local fakes.
- Reduce `unknown/needs manual read` share by half through better artifacts and intake.
- Keep quarantine under an agreed age threshold, for example no high-value test quarantined over 30 days without owner approval.

## Risks and tradeoffs

### Risk: more helpers can hide product bugs

If helpers wait too broadly, they can make real regressions look like slow convergence.

Mitigation:

- Helpers should wait for precise conditions and report last observed state.
- Product invariants should still have direct assertions.
- Do not replace race fixes with polling when the product contract requires ordering.

### Risk: lower parallelism slows CI

Reducing package parallelism may increase wall-clock time.

Mitigation:

- Apply lower parallelism only to resource-sensitive packages and platforms.
- Split pure unit packages from Postgres, PTY, network, and browser-heavy packages.
- Measure total runner minutes and PR latency, not just individual job duration.

### Risk: quarantine normalizes missing coverage

Skipping tests can become permanent.

Mitigation:

- Require owner, date, issue, and expiry.
- Track quarantine age publicly.
- Prefer narrower skips over removing broad suites.
- Require replacement coverage when the quarantined test protects critical behavior.

### Risk: flake detection burns CI budget

High-count stress workflows can be expensive.

Mitigation:

- Run targeted detection from labels and nightly schedules, not every PR.
- Use package ownership and changed-file mapping.
- Store signatures so repeated known failures do not trigger redundant expensive runs.

### Risk: false positives from grep-based linting

Some risky patterns are valid in helpers or intentionally slow tests.

Mitigation:

- Start linting as advisory.
- Allow local suppressions with reason comments.
- Promote only high-confidence patterns to blocking checks.

## Rollout plan

### Phase 1: Baseline and containment, 1 to 2 weeks

- Create the flake intake template and taxonomy labels.
- Start tracking normalized flake signatures.
- Add quarantine metadata requirements.
- Seed the known-pattern registry from this research.
- Pick the top 10 recurring signatures from recent CI and classify them.

Exit criteria:

- New flakes have category and signature.
- Quarantined tests have owner and expiry.
- A baseline exists for rerun rate, unique signatures, and time-to-triage.

### Phase 2: Deterministic helpers, 2 to 6 weeks

- Harden workspace/provisioner/agent lifecycle helpers.
- Add deterministic time guidance and fixtures for scheduling/metrics tests.
- Add isolated HTTP client/transport helpers.
- Add websocket/network readiness and close-drain helpers.
- Document package-specific parallelism defaults.

Exit criteria:

- New tests in high-risk areas use shared helpers by default.
- At least the top workspace lifecycle and timing recurring signatures are fixed or quarantined.
- Failure output includes last-observed state for the main lifecycle helpers.

### Phase 3: Detection automation, 4 to 8 weeks

- Add targeted flake detector workflow.
- Add nightly high-risk package stress suite.
- Add frontend/browser repeat suite with trace artifacts.
- Add trend dashboard for signatures, quarantine, reruns, and owner areas.

Exit criteria:

- Recurrent signatures are visible without manual log archaeology.
- Rerun-green failures update tracking instead of disappearing.
- `unknown/needs manual read` trends down.

### Phase 4: Enforcement, after signal stabilizes

- Promote the safest known-pattern checks to blocking.
- Require verification commands in flake fix PRs.
- Enforce quarantine expiry for high-value tests.
- Review category trends monthly and retire stale rules.

Exit criteria:

- Flake rate and rerun minutes decline without large PR latency regressions.
- Quarantine inventory remains small and fresh.
- Flake fix PRs consistently include root cause class and reproduction evidence.

## Highest-priority concrete actions

1. Build a lifecycle wait helper suite for workspace build, provisioner job, agent ready, and log drain states.
2. Add deterministic clock fixtures and ban exact boundary assertions using multiple `time.Now()` calls in scheduling/metrics tests.
3. Add isolated HTTP transport helpers and stop using shared default transports in parallel network/auth tests.
4. Add websocket/network readiness and close-drain helpers with better failure logs.
5. Create the flake signature tracker and make rerun-green failures update it.
6. Introduce quarantine metadata and expiry.
7. Add targeted `go test -count` and `-race` flake detector workflow for labeled tests and nightly high-risk packages.
8. Upload Playwright traces and locator state for all browser/e2e flake detection failures.
9. Tune CI parallelism by package class instead of globally widening timeouts.
10. Seed a known-pattern registry and use it as an advisory review checklist before turning any rule into a hard gate.

## Non-goals

- Eliminate every nondeterministic failure immediately.
- Make all tests slower by default.
- Treat every CI infrastructure issue as a product bug.
- Delete high-value coverage because it is noisy.
- Replace debugging with blanket timeout increases.
