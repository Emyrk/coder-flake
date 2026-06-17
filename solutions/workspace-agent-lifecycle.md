# workspace/agent/provisioner lifecycle potential flakes

## Scope

Audit of the current `/home/openclaw/coder` checkout for potential, not reproduced, nondeterministic tests in workspace, agent, provisioner, startup log, PTY, and lifecycle helper code.

This report uses the existing flake taxonomy. The closest categories are:

- workspace/agent lifecycle
- timing/eventual consistency
- concurrency/race
- networking/proxy/websocket
- resource exhaustion/timeout

## Files inspected

High-signal files read directly:

- `/home/openclaw/coder/coderd/workspacebuilds_test.go`
- `/home/openclaw/coder/coderd/coderdtest/coderdtest.go`
- `/home/openclaw/coder/coderd/provisionerdserver/acquirer_test.go`
- `/home/openclaw/coder/provisionerd/provisionerd_test.go`
- `/home/openclaw/coder/codersdk/agentsdk/logs_test.go`
- `/home/openclaw/coder/agent/boundarylogproxy/proxy_test.go`
- `/home/openclaw/coder/agent/agent_test.go`
- `/home/openclaw/coder/scaletest/reconnectingpty/run_test.go`
- `/home/openclaw/coder/scaletest/workspacetraffic/run_test.go`

Broad keyword scan also covered matching `_test.go` files under:

- `/home/openclaw/coder/coderd`
- `/home/openclaw/coder/provisionerd`
- `/home/openclaw/coder/agent`
- `/home/openclaw/coder/codersdk/agentsdk`
- `/home/openclaw/coder/scaletest/reconnectingpty`
- `/home/openclaw/coder/scaletest/workspacebuild`
- `/home/openclaw/coder/scaletest/workspacetraffic`
- `/home/openclaw/coder/enterprise/wsproxy`

## Findings

### Provisionerd reconnect path uses a fixed sleep as a sequencing barrier

- Category: concurrency/race, workspace/agent lifecycle, timing/eventual consistency
- Evidence:
  - `/home/openclaw/coder/provisionerd/provisionerd_test.go:940-947` starts a goroutine after the first acquire fails, closes the DRPC connection, stores `second=true`, sleeps for `50 * time.Millisecond`, then closes `failedChan`.
  - `/home/openclaw/coder/provisionerd/provisionerd_test.go:974-978` then waits for `completeChan` within `testutil.WaitShort` and shuts the server down.
- Why it can flake:
  - The sleep is trying to give the reconnect loop time to observe the closed connection and issue the second acquire. On a loaded runner, 50 ms can be too short; on a very fast run, it hides the real dependency.
  - The test has channels for the semantic events (`failChan`, `failedChan`, `completeChan`), but one lifecycle transition is still represented by wall-clock time.
- Proposed fix:
  - Replace the sleep with an explicit second-acquire handshake. Close a `secondAcquireStarted` channel from inside `acquireJobWithCancel` when `second.Load()` is true, then let the first acquire finish only after the second acquire is observed or after a context timeout.
  - Sketch:

```go
secondAcquireStarted := make(chan struct{})

acquireJobWithCancel: func(stream proto.DRPCProvisionerDaemon_AcquireJobWithCancelStream) error {
    if second.Load() {
        close(secondAcquireStarted)
        completeOnce.Do(func() { close(completeChan) })
        return nil
    }
    failOnce.Do(func() { close(failChan) })
    <-failedChan
    return nil
}

go func() {
    <-failChan
    _ = client.DRPCConn().Close()
    second.Store(true)
    require.Eventually(t, func() bool {
        select {
        case <-secondAcquireStarted:
            return true
        default:
            return false
        }
    }, testutil.WaitShort, testutil.IntervalFast)
    failedOnce.Do(func() { close(failedChan) })
}()
```

  - If calling `require` from the goroutine is undesirable, use `testutil.RequireReceive` in the main test path or make the goroutine send an error to a buffered channel.
- Validation:
  - `cd /home/openclaw/coder && go test ./provisionerd -run 'TestProvisionerd/.*/ReconnectAndFail' -count=100 -race`
  - Also run with low scheduler parallelism to stress reconnect ordering: `GOMAXPROCS=1 go test ./provisionerd -run 'TestProvisionerd/.*/ReconnectAndFail' -count=100 -race`
- Historical references:
  - `categories/concurrency-race.md` includes issue #9340, "Fail in goroutine after TestProvisionerd/InstantClose has completed", and issue #9895, `TestProvisionerd/MaliciousTar`, both centered on provisionerd shutdown/reconnect timing.
  - `categories/platform-os-specific-ci-behavior.md` includes early provisionerd context-cancellation fixes in PR #383 and PR #386.

### Provisioner acquirer test intentionally races pubsub processing with DB return

- Category: timing/eventual consistency, concurrency/race, workspace/agent lifecycle
- Evidence:
  - `/home/openclaw/coder/coderd/provisionerdserver/acquirer_test.go:165-168` says the desired behavior is retrying when a job posting arrives while a DB call is in progress.
  - `/home/openclaw/coder/coderd/provisionerdserver/acquirer_test.go:194-200` posts the job, documents a race between posting processing and DB return, then sleeps for `testutil.IntervalMedium` to try to hit the desired interleaving.
  - `/home/openclaw/coder/coderd/provisionerdserver/acquirer_test.go:202-208` then sends `sql.ErrNoRows`, sends the job, and expects success.
- Why it can flake:
  - The test is explicitly validating a race, but it selects the desired interleaving with a sleep instead of a pubsub-observed signal. If the pubsub goroutine runs later than `IntervalMedium`, the first DB return can win and the test can miss the path it claims to exercise.
  - This can produce false confidence: a pass might come from the other accepted interleaving, not the "posting processed first" path named in the comment.
- Proposed fix:
  - Add an observable hook to the fake store or acquirer test harness that records when the posting notification was consumed and the retry was queued.
  - Prefer a deterministic two-phase fake: block the first DB response, post the job, wait until the acquirer has received the pubsub notification, then release the first DB response with `sql.ErrNoRows`.
  - Sketch:

```go
postingObserved := make(chan struct{}, 1)
fs.onAcquireParams = func(params database.AcquireProvisionerJobParams) {
    if len(fs.params) == 2 {
        postingObserved <- struct{}{}
    }
}

postJob(t, ps, database.ProvisionerTypeEcho, provisionerdserver.Tags{})
testutil.RequireReceive(ctx, t, postingObserved)
require.NoError(t, fs.sendCtx(ctx, database.ProvisionerJob{}, sql.ErrNoRows))
require.NoError(t, fs.sendCtx(ctx, database.ProvisionerJob{ID: jobID}, nil))
```

  - If the production code has no hook point, make `newFakeOrderedStore` expose a channel closed when the second `AcquireProvisionerJob` call is attempted.
- Validation:
  - `cd /home/openclaw/coder && go test ./coderd/provisionerdserver -run '^TestAcquirer_RetriesPending$' -count=200 -race`
  - Run once before the fix with `GOMAXPROCS=1` and once after the fix to prove the sleep no longer controls the interleaving.
- Historical references:
  - `categories/concurrency-race.md` includes issue #13855, a `coderd/provisionerdserver` leaked goroutine flake, and PR #11453, a `TestHeartbeat` race around channel close/context behavior.
  - `ONE_PAGER.md` ranks workspace/agent/provisioner lifecycle as the best pilot category and calls out exact lifecycle waits over approximate timing.

### Workspace build helper may return after job completion but before dependent side effects are visible

- Category: workspace/agent lifecycle, timing/eventual consistency
- Evidence:
  - `/home/openclaw/coder/coderd/coderdtest/coderdtest.go:1245-1268` implements `AwaitWorkspaceBuildJobCompleted` by polling `client.WorkspaceBuild` until `workspaceBuild.Job.CompletedAt != nil`.
  - `/home/openclaw/coder/coderd/workspacebuilds_test.go:73-83` waits for the build helper, then separately polls audit logs until two records appear before reading the workspace build.
  - `/home/openclaw/coder/coderd/coderdtest/coderdtest.go:1419-1437` shows `WorkspaceAgentWaiter.Wait` has to re-fetch the workspace and wait again for `LatestBuild.Job.CompletedAt`, because build completion alone is not enough for agent resources/readiness.
- Why it can flake:
  - Several tests treat `AwaitWorkspaceBuildJobCompleted` as a full lifecycle barrier, but the helper only waits on the job's `CompletedAt` field from one endpoint. Audit logs, resources, agent state, app routes, and derived workspace fields can be updated or observed on different paths.
  - The audit-log polling in `workspacebuilds_test.go` is a local compensating wait. Other tests may assert derived state immediately after job completion without the domain-specific wait.
- Proposed fix:
  - Keep `AwaitWorkspaceBuildJobCompleted` narrow, but add purpose-built helpers for common dependent lifecycle points:
    - `AwaitWorkspaceBuildAuditLogs(t, auditor, count)`
    - `AwaitWorkspaceResources(t, client, workspaceID, matcher)`
    - `AwaitWorkspaceBuildOwnerFields(t, client, buildID, wantOwner)`
  - Update tests that assert derived state after build completion to wait for that exact state and log the last observed state on timeout.
  - For `workspacebuilds_test.go`, fold the audit wait into a named helper so future tests do not copy ad-hoc `len(logs) == N` polling.
- Validation:
  - `cd /home/openclaw/coder && go test ./coderd -run 'TestWorkspaceBuild' -count=50 -race`
  - Add a focused helper unit test that fails with a last-observed audit/resource snapshot when the expected side effect does not appear.
- Historical references:
  - `ONE_PAGER.md` says workspace and agent tests often assert before provisioners, agents, builds, PTYs, logs, or apps reach the expected lifecycle point.
  - `categories/workspace-agent-lifecycle.md` tracks this as the second-largest flake bucket and recommends waiting for exact lifecycle states: build created, provisioner job started, job complete, logs drained, agent ready, and app route available.
  - `categories/resource-exhaustion-timeout.md` includes PR #22883, where `AwaitWorkspaceAgents` context/agent readiness behavior contributed to a Git SSH flake.

### Startup log writer test has unsynchronized shared capture in parallel subtests

- Category: concurrency/race, workspace/agent lifecycle
- Evidence:
  - `/home/openclaw/coder/codersdk/agentsdk/logs_test.go:218-231` runs each startup log writer case with `t.Parallel()` and appends to `got` from the `send` callback without synchronization.
  - `/home/openclaw/coder/codersdk/agentsdk/logs_test.go:232-255` writes logs, optionally closes the writer, normalizes `CreatedAt`, then compares `got` to `want`.
  - `/home/openclaw/coder/codersdk/agentsdk/logs_test.go:379-415` has a separate flush-cancellation test that blocks `patchLogs` until context cancellation, showing this package already has asynchronous send/flush paths.
- Why it can flake:
  - If `LogsWriter` invokes the callback synchronously today, this is safe by implementation accident. If it buffers or dispatches sends asynchronously later, the unsynchronized slice append/read becomes a race and the equality assertion can run before all callback writes are visible.
  - The test name and area are startup-log lifecycle; losing or reordering a final partial line is exactly the kind of log-drain edge this audit is targeting.
- Proposed fix:
  - Make the capture thread-safe now, even if the current implementation is synchronous. Use a mutex around `got`, or better, write logs into a buffered channel and drain after `w.Close()`.
  - Always call `Close` before comparing cases that expect flushed partial lines. For cases that intentionally do not flush partial lines, assert that behavior before close and then close only for cleanup.
  - Sketch:

```go
var mu sync.Mutex
var got []agentsdk.Log
send := func(ctx context.Context, log ...agentsdk.Log) error {
    select {
    case <-ctx.Done():
        return ctx.Err()
    default:
    }
    mu.Lock()
    defer mu.Unlock()
    got = append(got, log...)
    return nil
}

// after writes and any required Close
mu.Lock()
gotCopy := slices.Clone(got)
mu.Unlock()
require.Equal(t, tt.want, gotCopy)
```

- Validation:
  - `cd /home/openclaw/coder && go test ./codersdk/agentsdk -run '^TestStartupLogsWriter_Write$' -count=200 -race`
  - If `LogsWriter` is later made async, add a test variant where `send` blocks on a channel to prove close drains before comparison.
- Historical references:
  - `categories/networking-proxy-websocket.md` includes PR #6492, "fix buffered provisioner job logs close flake", where log stream close/drain ordering caused intermittent failures.
  - `ONE_PAGER.md` explicitly lists logs drained as one of the workspace/agent lifecycle states tests should wait for.

### Boundary log proxy tests assert counts, then cancel the forwarder without a drained/closed acknowledgement

- Category: networking/proxy/websocket, workspace/agent lifecycle, timing/eventual consistency
- Evidence:
  - `/home/openclaw/coder/agent/boundarylogproxy/proxy_test.go:126-138` starts `srv.RunForwarder` under a cancellable context.
  - `/home/openclaw/coder/agent/boundarylogproxy/proxy_test.go:161-177` sends one log, polls until `len(logs) == 1`, cancels, then waits on `forwarderDone`.
  - `/home/openclaw/coder/agent/boundarylogproxy/proxy_test.go:204-229` sends five messages, polls until `len(logs) == 5`, cancels, then waits on `forwarderDone`.
  - `/home/openclaw/coder/agent/boundarylogproxy/proxy_test.go:252-290` sends from three concurrent connections, waits for count only, then cancels.
- Why it can flake:
  - Count-only waits do not prove all per-connection handlers have flushed, closed, and stopped. A late handler error after the test's count assertion can surface as a goroutine failure, leak, or context-canceled noise during cleanup.
  - This shape is close to prior Coder boundary and websocket flakes: the functional assertion passes, but cleanup races with a background forwarder.
- Proposed fix:
  - Add a test-visible drain signal to `fakeReporter` or the server harness. Wait for both expected report count and handler/forwarder idle before cancellation.
  - When canceling is the behavior under test, assert the forwarder returns `context.Canceled` or nil explicitly with a timeout, rather than a raw `<-forwarderDone`.
  - For concurrent connections, capture send errors through an error channel rather than calling `t.Errorf` from worker goroutines only.
- Validation:
  - `cd /home/openclaw/coder && go test ./agent/boundarylogproxy -run '^TestServer_(ReceiveAndForwardLogs|MultipleMessages|MultipleConnections)$' -count=200 -race`
  - Run with `-run TestServer_MultipleConnections -count=500 -race` after adding a drain/idle assertion.
- Historical references:
  - `categories/test-isolation-order-dependency.md` includes PR #21660, "test: fix flaky boundary test".
  - `categories/networking-proxy-websocket.md` includes multiple websocket close/read ordering flakes, including PR #6492 for buffered provisioner logs.

### Agent metadata timing test uses real elapsed time as the assertion oracle

- Category: timing/eventual consistency, resource exhaustion/timeout, workspace/agent lifecycle
- Evidence:
  - `/home/openclaw/coder/agent/agent_test.go:1926-1928` waits until two metadata entries exist.
  - `/home/openclaw/coder/agent/agent_test.go:1930-1964` then loops for `testutil.WaitMedium`, sleeping `testutil.IntervalMedium`, and compares observed script execution count to `time.Since(start) / reportInterval` with a 50% lower bound.
- Why it can flake:
  - The test already acknowledges backlog on loaded CI, but still treats wall-clock elapsed time as the oracle. A runner pause, GC stall, or CPU starvation can make the script execute fewer times than the lower bound even if the production loop is correct.
  - The failure mode is expensive because it only appears under scheduler pressure and reports as an agent behavior failure rather than a timing oracle failure.
- Proposed fix:
  - Replace real time with a fake clock if the metadata reporter can accept one.
  - If fake clock injection is too invasive, assert monotonic invariants rather than elapsed-count ratios: metadata remains present, error/value remain stable, and executions do not occur more frequently than the configured interval.
  - Preserve the "never speeds up" property by recording execution timestamps from the script/harness and asserting adjacent deltas are at least the interval, with scheduler slack, instead of deriving an expected count from wall time.
- Validation:
  - `cd /home/openclaw/coder && go test ./agent -run '^TestAgent_Metadata' -count=100 -race`
  - Stress timing separately with `GOMAXPROCS=1 go test ./agent -run '^TestAgent_Metadata' -count=50 -race`.
- Historical references:
  - `categories/concurrency-race.md` includes PR #8613, "test(agent): fix TestAgent_Metadata/Once flake", and PR #13553, "fix flake in TestWorkspaceAgent_Metadata_CatchMemoryLeak".
  - `categories/resource-exhaustion-timeout.md` tracks failures caused by CI scheduler/resource pressure and scoped context timeouts.

## Clean patterns / non-findings

- `/home/openclaw/coder/coderd/coderdtest/coderdtest.go:1362-1407` and `:1409-1437` use `testutil.Eventually` with caller-controlled contexts for `WorkspaceAgentWaiter`. That is the right general shape: wait for build completion, resources, and agent predicates instead of assuming `agenttest.New` is enough.
- `/home/openclaw/coder/scaletest/reconnectingpty/run_test.go:283-291` waits for workspace build completion, starts an agent, waits for workspace agents, then waits for the tailnet coordinator node before returning the agent ID. This is a good exact-readiness barrier.
- `/home/openclaw/coder/scaletest/workspacetraffic/run_test.go:80-139` waits for non-zero metrics before canceling the runner and then waits for `runDone`. The cancellation sequence is explicit enough that I did not mark it actionable, although it remains a useful model for other lifecycle tests.
- I did not flag stale Go loop variable capture patterns. Current Go range semantics make the old `tc := tc` advice stale unless a test has a different shared-state bug.

## Next steps

1. Replace the two sleep-based provisioner/acquirer sequencing tests first. They are the clearest potential flakes and have small, local fixes.
2. Add named lifecycle helpers for build side effects and log drains instead of copying local `Eventually(len(...) == N)` loops.
3. Run the validation commands above with `-race` and high `-count` before and after each fix. These are potential flakes from static audit, not confirmed reproduced failures.
