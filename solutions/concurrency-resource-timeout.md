# Concurrency and resource-timeout potential flakes

## Scope

This audit looked for potential nondeterministic test flakes in the current `/home/openclaw/coder` checkout, focused on goroutines, background assertions, cleanup races, unbounded fanout, PTY/process tests, shared resource pressure, and timeout diagnostics.

These are potential flakes, not confirmed bugs. I did not reproduce them. The findings are based on code evidence plus historical Coder flake patterns in `/home/openclaw/coder-flake-research`.

## Files inspected

Read directly:

- `/home/openclaw/coder/AGENTS.md`
- `/home/openclaw/coder/.claude/docs/TESTING.md`
- `/home/openclaw/coder/pty/start_test.go`
- `/home/openclaw/coder/enterprise/coderd/workspacequota_test.go`
- `/home/openclaw/coder/provisioner/terraform/install_test.go`
- `/home/openclaw/coder/coderd/activitybump_test.go`
- `/home/openclaw/coder/coderd/templates_test.go`
- `/home/openclaw/coder/cli/server_test.go`
- `/home/openclaw/coder/aibridge/internal/integrationtest/circuit_breaker_internal_test.go`
- `/home/openclaw/coder/enterprise/coderd/prebuilds/reconcile_test.go`
- `/home/openclaw/coder/agent/agentproc/api_test.go`

Scanned across 1,013 Go test files for:

- `go func` blocks containing `require.*`, `assert.*`, or `t.Fatal`
- `time.Sleep` in tests
- `context.WithTimeout` in tests
- `errgroup` usage without local `SetLimit`
- goroutine fanout loops
- `goleak.Verify` coverage

Knowledge-base inputs used:

- `/home/openclaw/coder-flake-research/ONE_PAGER.md`
- `/home/openclaw/coder-flake-research/categories/concurrency-race.md`
- `/home/openclaw/coder-flake-research/categories/resource-exhaustion-timeout.md`
- `/home/openclaw/coder-flake-research/categories/workspace-agent-lifecycle.md`
- `/home/openclaw/coder-flake-research/categories/timing-eventual-consistency.md`
- `/home/openclaw/coder-flake-research/categories/platform-os-specific-ci-behavior.md`
- `/home/openclaw/coder-flake-research/notes/common-solutions.md`
- `/home/openclaw/coder-flake-research/notes/proposed-solutions.md`
- `/home/openclaw/.hermes/profiles/fast-reviewer/skills/emyrk/flake-audit/references/patterns.md`

## Findings

### Background goroutines call test assertions and test helpers

- Category: `concurrency/race`, `resource exhaustion/timeout`
- Evidence:
  - `/home/openclaw/coder/pty/start_test.go:68-91` starts a reader goroutine and calls `testutil.NewTerminalReader(t, ...)`, `assert.NoError(t, err, ...)`, and `assert.NoError(t, err)` inside it.
  - `/home/openclaw/coder/enterprise/coderd/workspacequota_test.go:154-161` starts four goroutines that call `coderdtest.CreateWorkspace(t, ...)`, `coderdtest.AwaitWorkspaceBuildJobCompleted(t, ...)`, and `assert.Equal(t, ...)` inside the worker goroutine.
  - `/home/openclaw/coder/provisioner/terraform/install_test.go:142-149` starts eight goroutines and calls `assert.NoError(t, err)` inside each goroutine.
  - `/home/openclaw/coder/enterprise/coderd/prebuilds/reconcile_test.go:1976-2004` starts five goroutines; each creates test loggers and clocks with `t`, then calls `require.True(t, lockObtained)` inside the reconciliation callback.
- Why it can flake:
  - This matches the flake-audit pattern `Assertions from background goroutines`.
  - Test helpers often call `require.*` or `t.Helper()` internally. A `require` failure in a worker goroutine calls `FailNow` in the wrong goroutine, which can leave the parent test running, skip cleanup ordering, or surface as a late failure.
  - Historical Coder flakes include this exact shape: `concurrency-race.md` cites issue #9340 and PR #9709 for a goroutine calling `Fail` after `TestProvisionerd/InstantClose` completed. The common-solutions playbook calls out `Fail in goroutine after Test... has completed` and says to scope errors to the test goroutine.
- Proposed fix:
  - Return worker errors through a channel or `errgroup.Group`.
  - Keep all `require.*`, `assert.*`, and helper calls that take `testing.TB` on the parent test goroutine.
  - For concurrent API/workspace operations, define worker functions that return typed results plus `error`, then assert after `wg.Wait()` or `g.Wait()`.
  - For `/home/openclaw/coder/enterprise/coderd/prebuilds/reconcile_test.go`, use atomic counters or an error channel inside the callback instead of `require.True(t, ...)` from the contending goroutines.
- Validation:
  - `go test -race -count=100 ./pty -run Test_Start_truncation`
  - `go test -race -count=100 ./enterprise/coderd -run TestWorkspaceQuota`
  - `go test -race -count=100 ./provisioner/terraform -run TestInstall`
  - `go test -race -count=100 ./enterprise/coderd/prebuilds -run TestReconciliationLock`
- Historical references:
  - `categories/concurrency-race.md`: issue #9340, PR #9709, goroutine failure after test completion.
  - `notes/proposed-solutions.md`: concurrency guardrails, especially "test logging helpers that call `t.Helper()` and never call `t.Fatal` from non-test goroutines".
  - `references/patterns.md`: `Assertions from background goroutines`.

### Resource-heavy fanout runs inside normal tests without a local budget

- Category: `resource exhaustion/timeout`, `workspace/agent lifecycle`, `database/transactions/migrations`
- Evidence:
  - `/home/openclaw/coder/enterprise/coderd/workspacequota_test.go:152-164` concurrently creates four full workspaces, waits for each build job, then verifies quota.
  - `/home/openclaw/coder/provisioner/terraform/install_test.go:135-149` concurrently runs eight Terraform installs through a local proxy and shared install directory.
  - `/home/openclaw/coder/enterprise/coderd/prebuilds/reconcile_test.go:1974-2007` starts five reconcilers against the same DB and provisioner store, each holding the reconciliation lock path for `time.Second`.
- Why it can flake:
  - This matches `Unbounded fanout in CI-sensitive tests`.
  - The counts are small in isolation, but these tests run under package-level `t.Parallel()` and CI package parallelism. Coder's corpus repeatedly shows that Postgres, workspace builds, PTYs, provisioners, and network-heavy tests turn runner pressure into timeout flakes.
  - Workspace quota and prebuild reconciliation tests also hit lifecycle and DB-backed state. Resource pressure can make them fail as lifecycle timeouts rather than obvious CPU or DB saturation.
- Proposed fix:
  - Make these tests explicitly stress tests, or bound them with a local limit that reflects the invariant being tested.
  - Where concurrency itself is the behavior under test, add timeout diagnostics that print runner/package context and last observed build/reconciler state.
  - Prefer `errgroup.WithContext` plus `SetLimit` for worker orchestration and error collection.
  - For workspace quota, consider using direct DB setup or a narrower fake provisioner path if the test only needs quota accounting, not full concurrent workspace lifecycle coverage.
- Validation:
  - `go test -race -count=100 -parallel=16 ./enterprise/coderd -run TestWorkspaceQuota`
  - `go test -race -count=100 -parallel=16 ./enterprise/coderd/prebuilds -run TestReconciliationLock`
  - `go test -race -count=100 -parallel=16 ./provisioner/terraform -run TestInstall`
  - Run the same commands with `-parallel=1` and compare recurrence. If failures disappear only under low parallelism, it supports the resource-pressure diagnosis.
- Historical references:
  - `categories/resource-exhaustion-timeout.md`: PR #26009 reduced `flake-go` parallelism after a 4-vCPU runner hit worst-case 64 in-flight subtests and OOMed.
  - `categories/database-transactions-migrations.md` via `notes/common-solutions.md`: PR #12700 fixed a flake caused by concurrent usage of the same deployment in workspace app tests.
  - `notes/proposed-solutions.md`: right-size CI parallelism by job and package; cap Postgres, PTY, browser, and network-heavy package parallelism separately from pure unit tests.

### Sleeps are used as readiness or quiet-period synchronization

- Category: `timing/eventual consistency`, `workspace/agent lifecycle`, `resource exhaustion/timeout`
- Evidence:
  - `/home/openclaw/coder/cli/server_test.go:335-341` starts `coder server`, waits for access URL, then sleeps `testutil.WaitShort` to wait for "more logs to be printed" before counting terminal lines.
  - `/home/openclaw/coder/coderd/activitybump_test.go:210-216` sleeps three seconds so network traffic surpasses the bump threshold, then opens SSH and asserts the deadline bumped.
  - `/home/openclaw/coder/coderd/activitybump_test.go:248-254` repeats the same three-second bump-threshold sleep in the max-deadline subtest.
  - `/home/openclaw/coder/coderd/templates_test.go:912-920` sleeps five milliseconds so `updatedAt` is not "too close together" before updating template metadata.
  - `/home/openclaw/coder/aibridge/internal/integrationtest/circuit_breaker_internal_test.go:463-465` sleeps `cbConfig.Timeout + 10*time.Millisecond` to reach half-open state.
- Why it can flake:
  - This matches `time.Sleep for synchronization`.
  - Fixed sleeps encode a timing guess. Under slow CI, the sleep can still be too short. Under fast execution, it hides the real readiness condition and burns wall time.
  - The template metadata sleep is especially close to historical timestamp precision flakes: the comment already says the test can fail if timestamps are too close together.
- Proposed fix:
  - Replace sleep-for-readiness with condition waits that report last observed state.
  - In `cli/server_test.go`, wait for a stable log quiet period, a specific server-ready marker, or use server internals/fakes to collect startup log output deterministically.
  - In `activitybump_test.go`, inject a clock or expose a test threshold so the bump condition can be advanced deterministically instead of wall-clock sleeping.
  - In `templates_test.go`, use an injected DB clock or compare a server-controlled version/timestamp derived from a deterministic fixture. Avoid requiring a real 5ms precision gap.
  - In circuit-breaker tests, use a fake clock if the circuit-breaker implementation supports it, or poll the circuit state with last observed state in the failure message.
- Validation:
  - `go test -count=100 ./cli -run 'TestServer/SpammyLogs'`
  - `go test -count=100 ./coderd -run Test_ActivityBumpWorkspace`
  - `go test -count=100 ./coderd -run 'TestPatchTemplateMeta/(Update|AGPL_Deprecated)'`
  - `go test -count=100 ./aibridge/internal/integrationtest -run TestCircuitBreaker`
- Historical references:
  - `categories/timing-eventual-consistency.md`: issue #3420, `TestServer/Prometheus` asserted before metrics were available; PR #19450 fixed a flake from two `time.Now()` calls; PR #21396 used deterministic time; PR #23830 fixed a timezone boundary race.
  - `categories/platform-os-specific-ci-behavior.md`: issue #14877 and PR #14888 removed a redundant API key refresh test likely affected by DB time precision; PR #5776 widened a time range check causing macOS flakes.
  - `references/patterns.md`: `time.Sleep for synchronization`, `Exact timestamp equality after persistence`.

### Long-running goroutines and servers are closed but not always joined

- Category: `resource exhaustion/timeout`, `concurrency/race`, `networking/proxy/websocket`
- Evidence:
  - `/home/openclaw/coder/provisioner/terraform/install_test.go:129-133` starts `go proxy.srv.Serve(proxy.listener)` and registers cleanup that calls `proxy.srv.Close()`, but does not wait for the server goroutine to exit or assert an expected terminal error.
  - `/home/openclaw/coder/cli/server_test.go:333-341` attaches a PTY, starts a long-running server with `clitest.Start(t, inv)`, then uses wall-clock sleep before reading terminal output. There is no explicit waiter for a clean process state in this subtest.
- Why it can flake:
  - This matches `Leaked goroutines` and overlaps the lifecycle pattern around PTY/process cleanup.
  - Closing a server without joining its `Serve` goroutine can hide unexpected serve errors and leave cleanup ordering dependent on scheduling.
  - Long-running PTY/process tests are a known Coder hotspot. Cleanup cancellation can race output readers or process waiters, which appears as timeout, missing output, or late goroutine failures.
- Proposed fix:
  - Wrap ad hoc servers in a helper that returns a shutdown function which closes the server and waits for `Serve` to return. Treat `http.ErrServerClosed`, `net.ErrClosed`, or the listener's expected close error as success, and report any other error from the test goroutine.
  - For CLI process tests, prefer a `StartWithWaiter`-style lifecycle when the command is expected to terminate. For intentionally long-running server commands, add explicit reader-drain or process-state diagnostics before cleanup cancellation.
- Validation:
  - `go test -race -count=100 ./provisioner/terraform -run TestInstall`
  - `go test -race -count=100 ./cli -run 'TestServer/SpammyLogs'`
  - Add `goleak.VerifyNone(t)` around the narrowed tests after fixing, if package-level goleak does not already cover the case.
- Historical references:
  - `categories/workspace-agent-lifecycle.md`: issue #2603 and PRs #2732/#2783/#5353 around provisioner job log ordering and log drains; PR #2456 wrote server URL only after signal listening was ready.
  - `categories/concurrency-race.md`: PR #9709 verified a goroutine/instant-close fix with `go test -race -count=10000`.
  - `references/patterns.md`: `Leaked goroutines`, `Unchecked context cancellation in deferred cleanup`, `CLI expecter without waiter`.

### Timeout failures would lack last-observed state or runner context in several high-risk tests

- Category: `resource exhaustion/timeout`, `platform/os-specific CI behavior`, `workspace/agent lifecycle`
- Evidence:
  - `/home/openclaw/coder/pty/start_test.go:61-64` creates a `context.WithTimeout(context.Background(), testutil.WaitSuperLong)` around PTY command startup and reader work.
  - `/home/openclaw/coder/pty/start_test.go:99-110` reports only `cmd.Wait() timed out` or `read timed out`, without last bytes observed, command state, platform, or reader state.
  - `/home/openclaw/coder/cli/server_test.go:337-341` has a readiness wait followed by a blind sleep; if the assertion later fails, the output does not explain whether the server was still emitting logs, the PTY reader lagged, or the runner was slow.
  - `/home/openclaw/coder/enterprise/coderd/prebuilds/reconcile_test.go:1994-2004` lock contention work sleeps inside the critical section; timeout would not identify which goroutine held or waited for the DB lock.
- Why it can flake:
  - This is not a flake by itself, but it raises the cost of diagnosing resource flakes. The research repo repeatedly found timeout symptoms hiding lifecycle, platform, and runner-capacity root causes.
  - The area-specific scope called out timeouts lacking runner/package context; these tests are in PTY/process and DB-lock hotspots where opaque timeouts are common.
- Proposed fix:
  - Use `require.Eventuallyf` or helper-level timeout errors that include last observed command output, process state, lock holder/waiter count, OS/arch, and package parallelism where practical.
  - Add state capture at lifecycle boundaries: server started, URL ready, last terminal line, reader EOF, command exit status, DB lock acquisition count.
  - Keep timeouts, but make them diagnostic rather than just larger.
- Validation:
  - `go test -count=100 ./pty -run Test_Start_truncation`
  - `go test -count=100 ./cli -run 'TestServer/SpammyLogs'`
  - `go test -count=100 ./enterprise/coderd/prebuilds -run TestReconciliationLock`
  - Force a short local timeout during review to confirm the failure message includes last observed state before restoring the normal budget.
- Historical references:
  - `categories/resource-exhaustion-timeout.md`: issue #8968, workspace watcher timed out waiting for an event; PR #26009, runner-capacity flake from high parallelism.
  - `categories/platform-os-specific-ci-behavior.md`: common fixes include recording OS, CPU, memory, shell, and package parallelism in failure output.
  - `notes/proposed-solutions.md`: improve failure artifacts with workspace build state, provisioner job state, last provisioner log, agent connection state, websocket state, and runner metadata.

## Clean patterns / non-findings

- I did not flag stale Go loop-variable captures. The audit intentionally avoided `tc := tc` or `x := x` recommendations solely for `t.Parallel()` range loops.
- Many goroutines found by the scan were joined correctly through `sync.WaitGroup`, channels, or package-level helpers. I only elevated examples where the goroutine also uses `testing.TB` helpers/assertions, resource-heavy work, or opaque lifecycle sleeps.
- `goleak.Verify` exists in many high-risk packages, including `pty`, `provisionerd`, `coderd`, `agent`, `tailnet`, and several chat/aibridge packages. That reduces but does not eliminate the risk from goroutine assertions or cleanup ordering.
- `context.WithTimeout` is widespread in Coder tests. I did not treat it as a finding by itself. It becomes actionable here only when combined with PTY/process/DB-lock hotspots and low-diagnostic timeout messages.
- Some `time.Sleep` calls model product time directly, such as TTL expiry. Those should move to fake clocks when practical, but I did not flag every instance as blocking.

## Next steps

1. Fix the background assertion pattern first. It is the highest-signal concurrency smell and maps directly to prior Coder race flakes.
2. Pick one high-resource test from this report and run the proposed `-race -count=100 -parallel=16` command before changing it. Use the result to decide whether it belongs in normal PR CI or a targeted stress suite.
3. Replace the shortest sleeps that guard timestamp precision or readiness with fake clocks or explicit condition waits. Start with `templates_test.go` and `activitybump_test.go` because Coder has multiple historical time-boundary flakes.
4. Add richer timeout diagnostics to PTY/process and reconciliation-lock tests before widening any timeout.
