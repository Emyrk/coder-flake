# networking/proxy/websocket potential flakes

## Scope

Audit of the current `/home/openclaw/coder` checkout for potential, not reproduced, nondeterministic failures in network-heavy tests. This report uses the Coder flake research taxonomy and focuses on:

- networking/proxy/websocket
- workspace/agent lifecycle
- concurrency/race
- timing/eventual consistency

These are potential flakes. They need targeted reproduction with repeated runs, race detector, or CI evidence before being treated as confirmed bugs.

## Files inspected

High-signal files read directly by the Kanban audit:

- `/home/openclaw/coder/enterprise/coderd/workspaceproxy_test.go`
- `/home/openclaw/coder/enterprise/tailnet/pgcoord_internal_test.go`
- `/home/openclaw/coder/tailnet/conn_test.go`
- `/home/openclaw/coder/agent/agent_test.go`
- `/home/openclaw/coder/agent/agentgit/agentgit_test.go`
- `/home/openclaw/coder/scaletest/workspacetraffic/run_test.go`

The audit also loaded:

- `categories/networking-proxy-websocket.md`
- `categories/workspace-agent-lifecycle.md`
- `categories/concurrency-race.md`
- `categories/timing-eventual-consistency.md`
- `notes/common-solutions.md`
- `notes/proposed-solutions.md`
- `flake-audit/references/patterns.md`
- `/home/openclaw/coder/AGENTS.md`
- `/home/openclaw/coder/.claude/docs/TESTING.md`

## Findings

### Assertions run inside workspace traffic goroutines

- Category: concurrency/race, networking/proxy/websocket, resource exhaustion/timeout
- Evidence:
  - `/home/openclaw/coder/scaletest/workspacetraffic/run_test.go:116-126`
  - `/home/openclaw/coder/scaletest/workspacetraffic/run_test.go:236-246`
  - `/home/openclaw/coder/scaletest/workspacetraffic/run_test.go:336-346`
- Why it can flake:
  - The tests call `assert.NoError` and `assert.Eventually` inside spawned goroutines. That matches the known flake pattern: assertions from a non-test goroutine can race test completion, cleanup, and failure reporting.
  - If the goroutine fails near cleanup, the main test path may already be returning or cancelling contexts, producing late or misleading failures.
- Proposed fix:
  - Make the goroutines report structured errors/results over channels.
  - Assert from the main test goroutine after receiving from `runDone`, `gotMetrics`, or equivalent synchronization channels.
  - Keep spawned goroutines dumb: collect data, return error, never call `t.Fatal`, `require.*`, or `assert.*` directly.
- Validation:
  - `go test ./scaletest/workspacetraffic -run TestRun -count=50`
  - `go test -race ./scaletest/workspacetraffic -run TestRun -count=20`
- Historical references:
  - `categories/concurrency-race.md`, especially the background goroutine assertion examples.
  - `categories/networking-proxy-websocket.md`, for network traffic tests that need explicit route/message/close synchronization.

### Workspace proxy timestamp boundary relies on a 1 ms sleep

- Category: timing/eventual consistency, database/transactions/migrations, networking/proxy/websocket
- Evidence:
  - `/home/openclaw/coder/enterprise/coderd/workspaceproxy_test.go:458`
  - `/home/openclaw/coder/enterprise/coderd/workspaceproxy_test.go:468`
- Why it can flake:
  - The test sleeps `1ms` so `UpdatedAt` becomes greater than `CreatedAt`. That is a wall-clock precision assumption around DB-backed state.
  - On CI, clock precision, scheduling, DB round trips, and platform behavior can make a 1 ms boundary too tight.
- Proposed fix:
  - Avoid asserting the semantic behavior through a tiny wall-clock delta.
  - Prefer a controlled/injected timestamp source if available.
  - Or assert the observable re-registration effect directly, rather than requiring `UpdatedAt > CreatedAt` after a fixed sleep.
- Validation:
  - `go test ./enterprise/coderd -run TestWorkspaceProxy -count=100`
  - Repeat under the race detector if the narrowed test is cheap enough: `go test -race ./enterprise/coderd -run TestWorkspaceProxy -count=25`
- Historical references:
  - `categories/timing-eventual-consistency.md`, for exact time boundary assertions and injected-clock fixes.
  - `categories/database-transactions-migrations.md`, for DB timestamp precision issues.

### Tailnet pgcoord test uses sleep to prove absence of async work

- Category: networking/proxy/websocket, timing/eventual consistency, concurrency/race
- Evidence:
  - `/home/openclaw/coder/enterprise/tailnet/pgcoord_internal_test.go:432-437`
- Why it can flake:
  - The test sleeps before closing the coordinator to give async work time to happen, because it is asserting a DB call is absent.
  - That proves only that nothing happened during the sleep interval. It does not prove the coordinator drained the relevant async work queue or reached a stable idle state.
- Proposed fix:
  - Expose or use a deterministic drain/barrier for the coordinator work queue.
  - If the test uses a mock clock, advance through the relevant lifecycle and wait on a concrete idle state before asserting gomock expectations.
- Validation:
  - `go test ./enterprise/tailnet -run Test.*PgCoord -count=100`
  - `go test -race ./enterprise/tailnet -run Test.*PgCoord -count=25`
- Historical references:
  - `categories/networking-proxy-websocket.md`, for distributed route/proxy readiness failures.
  - `categories/timing-eventual-consistency.md`, for sleeps that stand in for explicit synchronization.

### Tailnet connection test waits 10 seconds for absence of disco endpoints

- Category: networking/proxy/websocket, timing/eventual consistency
- Evidence:
  - `/home/openclaw/coder/tailnet/conn_test.go:456-458`
- Why it can flake:
  - The test waits 10 seconds because there is no way to force Disco to send endpoints immediately, then asserts no endpoints exist.
  - This is slow and still timing-dependent. It depends on what does not happen during an arbitrary interval instead of observing a deterministic state transition.
- Proposed fix:
  - Add a test hook or deterministic magicsock/disco signal for endpoint publication.
  - Narrow the assertion to a state transition that the test can observe without sleeping.
  - If absence really is the contract, expose an idle/drained state from the component under test so the test can assert after the system has reached quiescence.
- Validation:
  - `go test ./tailnet -run TestConn -count=100`
  - `go test -race ./tailnet -run TestConn -count=25`
- Historical references:
  - `categories/networking-proxy-websocket.md`, largest historical Coder flake category.
  - `categories/timing-eventual-consistency.md`, for fixed waits around async state.

## Clean patterns / non-findings

- The audit found Coder already uses many explicit helpers and eventual assertions in network-heavy areas.
- The strongest actionable findings are not generic network complexity. They are specific synchronization gaps: assertions in goroutines, fixed sleeps, and absence assertions without a drain/idle signal.
- No recommendation here depends on stale Go loop-variable capture advice.

## Next steps

1. Start with `scaletest/workspacetraffic/run_test.go`, because assertion-from-goroutine is the highest-signal blocking pattern.
2. Replace the two sleep-based absence/boundary checks with deterministic barriers or semantic assertions.
3. Add route/close/drain test helper ideas to the networking helper backlog if these patterns repeat across more tailnet/wsproxy tests.
