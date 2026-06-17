# Timing and eventual consistency

Tests check async state before convergence or compare wall-clock values too tightly.

## Count

| references | issues | PRs |
| ---: | ---: | ---: |
| 46 | 15 | 31 |

## Why it flakes

This category is where bigger timeouts are most tempting. Sometimes they help, but they often hide missing synchronization.

## Common fixes

- Inject clocks or pass explicit time values in scheduling, TTL, metrics, and status tests.
- Poll for the actual condition and print the last observed state on timeout.
- Avoid multiple `time.Now()` calls around boundary assertions.
- Widen time ranges only when the product genuinely measures wall-clock elapsed time.
- Use deterministic fixtures for timezone and precision boundaries.

## Code examples

These examples are illustrative patterns for the category, not direct patches against one specific test.

<details>
<summary>Code examples</summary>

### Bad: sleep and hope the async state converged

```go
triggerReconciliation(ctx)
time.Sleep(2 * time.Second)

got, err := store.GetStatus(ctx, id)
require.NoError(t, err)
require.Equal(t, StatusReady, got)
```

### Better: poll the condition and report the last observed value

```go
triggerReconciliation(ctx)

var last Status
require.Eventuallyf(t, func() bool {
	got, err := store.GetStatus(ctx, id)
	if err != nil {
		return false
	}
	last = got
	return got == StatusReady
}, testutil.WaitLong, testutil.IntervalFast, "last status: %s", last)
```

### Bad: compare against a second `time.Now()` at the boundary

```go
expiresAt := time.Now().Add(time.Hour)
require.True(t, expiresAt.After(time.Now().Add(59*time.Minute)))
```

### Better: inject one clock value and derive expectations from it

```go
clock := quartz.NewMock(t)
now := clock.Now()
expiresAt := now.Add(time.Hour)

require.Equal(t, now.Add(time.Hour), expiresAt)
```

</details>

## Suggested first slice

Add deterministic clock guidance and search for exact boundary assertions around scheduling and metrics tests.

<details>
<summary>References (46)</summary>

`solved by` is the author of the merged PR, either the reference itself or a linked fix PR. It is blank when the corpus did not identify a merged fix PR.

| ref | type | title | status | solved by | evidence |
| --- | --- | --- | --- | --- | --- |
| [issue #3420](https://github.com/coder/coder/issues/3420) | issue | `TestServer/Prometheus` test flake | closed |  | `TestServer/Prometheus` test flake c.f. https://github.com/coder/coder/actions/runs/2821006778/attempts/1 ``` === Failed === FAIL: cli TestServer/Prometheus (0.19s) server_test.go:428: Error Trace: /home/runner/work/coder/coder/cli/server_test.go:428 Error: Should be true Test: TestServer/Prometheus --- FAIL: TestSe... |
| [issue #5323](https://github.com/coder/coder/issues/5323) | issue | flaky: coderd/prometheusmetrics TestWorkspaces/Multiple | closed |  | flaky: coderd/prometheusmetrics TestWorkspaces/Multiple Spotted in: https://github.com/coder/coder/actions/runs/3630546787/jobs/6124020920 ``` === FAIL: coderd/prometheusmetrics TestWorkspaces/Multiple (5.00s) prometheusmetrics_test.go:227: Error Trace: /home/runner/work/coder/coder/coderd/prometheusmetrics/promethe... |
| [issue #6481](https://github.com/coder/coder/issues/6481) | issue | flake: coderd_test.TestTemplateMetrics | closed |  | flake: coderd_test.TestTemplateMetrics `TestTemplateMetrics` in `coderd/templates_test.go` is disabled because it flakes often in my experience when running the full test suite. flake: coderd_test.TestTemplateMetrics `TestTemplateMetrics` in `coderd/templates_test.go` is disabled because it flakes often in my experi... |
| [issue #9168](https://github.com/coder/coder/issues/9168) | issue | test flake: TestScaleTestDashboard fails intermittently | closed |  | ...: workspace app stats collector started t.go:85: 2023-08-18 09:07:17.991 [debu] metrics_cache: deployment stats metrics refreshed took=14.978µs interval=5m0s t.go:85: 2023-08-18 09:07:18.004 [debu] metrics_cache: template daus metrics refreshed took=9.951814ms interval=1h0m0s t.go:85: 2023-08-18 09:07: test flake... |
| [issue #9341](https://github.com/coder/coder/issues/9341) | issue | test flake: agent/reaper TestReap: no child processes | closed |  | ...k exec: %w", err) } go catchSignals(pid, opts.CatchSignals) var wstatus syscall.WaitStatus // test flake: agent/reaper TestReap: no child processes ``` === Failed === FAIL: agent/reaper TestReap (0.00s) reaper_test.go:40: Error Trace: /home/cian/src/coder/coder/agent/reaper/reaper_test.go:40 Error: Received unexp... |
| [issue #9785](https://github.com/coder/coder/issues/9785) | issue | flake: TestPostWorkspacesByOrganization/Create | closed |  | ...me/runner/actions-runner/_work/coder/coder/coderd/workspaces_test.go:488 Error: Condition never satisfied Test: TestPostWorkspacesByOrganization/Create ``` Seen on [main](https://github.com/coder/coder/actions/runs/6239179576/job/16936561535) flake: TestPostWorkspacesByOrganization/Create ``` workspaces_test.go:4... |
| [issue #9873](https://github.com/coder/coder/issues/9873) | issue | test flake: Test_parseInsightsInterval_week: Query param "end_time" must have the clock set to 00:00:00 | closed |  | test flake: Test_parseInsightsInterval_week: Query param "end_time" must have the clock set to 00:00:00 Seen here: - https://github.com/coder/coder/actions/runs/6306577063/job/17122030191 - https://github.com/coder/coder/actions/runs/6306543246/job/17121847210 - https://github.com/coder/coder/actions/runs/6306335311... |
| [issue #10600](https://github.com/coder/coder/issues/10600) | issue | flake: Test_parseInsightsStartAndEndTime | closed |  | flake: Test_parseInsightsStartAndEndTime ``` === FAIL: coderd Test_parseInsightsInterval_week/9_days_(7_+_2)_are_not_acceptable (0.00s) insights_internal_test.go:239: Status: 400 insights_internal_test.go:240: Body: { "message": "Query parameter has invalid value.", "validations": [ { "field": "end_time", "detail":... |
| [issue #11011](https://github.com/coder/coder/issues/11011) | issue | flake: Test_ActivityBumpWorkspace | closed |  | flake: Test_ActivityBumpWorkspace https://github.com/coder/coder/actions/runs/7083108479/job/19274946870#step:5:317 ``` === FAIL: coderd Test_ActivityBumpWorkspace/TemplateDisallowsUserAutostop/US/Arizona (0.04s) activitybump_internal_test.go:260: Error Trace: /home/runner/actions-runner/_work/coder/coder/coderd/act... |
| [issue #11097](https://github.com/coder/coder/issues/11097) | issue | flake: TestUserActivityInsights_BadRequest | closed |  | flake: TestUserActivityInsights_BadRequest Seen on [main](https://github.com/coder/coder/actions/runs/7136073396/job/19433957956) ``` === FAIL: coderd TestUserActivityInsights_BadRequest (0.01s) t.go:84: 2023-12-08 01:16:25.938 [debu] acquirer: subscribed to job postings t.go:84: 2023-12-08 01:16:25.938 [debu] works... |
| [issue #12018](https://github.com/coder/coder/issues/12018) | issue | flake: WorkspacePage › requests a delete job when the user presses Delete and confirms | closed |  | ...ext 2-ish weeks @Parkreiner just want to bump in your notifs. No worries on the delay, feel free to unassign if you're backlog is too full. Yeah, I'll go ahead and un-assign myself for now From the error messages, it looks like we are using the right selectors for checking whether something is on screen. We're us... |
| [issue #12509](https://github.com/coder/coder/issues/12509) | issue | flake: insights | closed; linked_fix_merged | [@mafredri](https://github.com/mafredri) | flake: insights From https://github.com/coder/coder/actions/runs/8229639076/job/22501248571?pr=12468 ```bash insights_test.go:108: Error Trace: /home/runner/actions-runner/_work/coder/coder/coderd/insights_test.go:108 Error: Not equal: expected: &codersdk.DAUsResponse{Entries:[]codersdk.DAUEntry{codersdk.DAUEntry{Da... |
| [issue #12938](https://github.com/coder/coder/issues/12938) | issue | flake: TestCollectInsights error log dropped | closed |  | flake: TestCollectInsights error log dropped Seen on: https://github.com/coder/coder/runs/23674923557 ``` t.go:108: 2024-04-10 18:22:29.578 [erro] coderd.metrics_cache: refresh error="sql: no rows in result set" *** slogtest: log detected at level ERROR; TEST FAILURE *** ``` flake: TestCollectInsights error log drop... |
| [issue #13931](https://github.com/coder/coder/issues/13931) | issue | flake: `TestProvisionerDaemon_SessionToken/PrometheusEnabled` | closed |  | flake: `TestProvisionerDaemon_SessionToken/PrometheusEnabled` https://github.com/coder/coder/actions/runs/9987661978/job/27602490812?pr=13902 ``` provisionerdaemons_test.go:207: Error Trace: /home/runner/work/coder/coder/enterprise/cli/provisionerdaemons_test.go:207 Error: Condition never satisfied Test: TestProvisi... |
| [issue #14891](https://github.com/coder/coder/issues/14891) | issue | flake: `TestUserActivityInsights_SanityCheck` | closed |  | flake: `TestUserActivityInsights_SanityCheck` https://github.com/coder/coder/actions/runs/11123116592/job/30905878629?pr=14869 flake: `TestUserActivityInsights_SanityCheck` https://github.com/coder/coder/actions/runs/11123116592/job/30905878629?pr=14869 |
| [PR #6350](https://github.com/coder/coder/pull/6350) | PR | chore: increase activitybump deadline duration to fix flake | closed; merged | [@kylecarbs](https://github.com/kylecarbs) | chore: increase activitybump deadline duration to fix flake This is a bad fix because the test is still dependant on time, but it's still an improvement. chore: increase activitybump deadline duration to fix flake This is a bad fix because the test is still dependant on time, but it's still an improvement. chore: in... |
| [PR #8576](https://github.com/coder/coder/pull/8576) | PR | test(testutil): increase wait times to reduce flakes | closed; merged | [@mafredri](https://github.com/mafredri) | test(testutil): increase wait times to reduce flakes This is a test to see if https://github.com/coder/coder/pull/8561 is a culprit to increased flakeyness by improving in-memory networking performance enough to more easily cause 5-second delays due to WireGuard handshake retry. test(testutil): increase wait times t... |
| [PR #10252](https://github.com/coder/coder/pull/10252) | PR | fix(scaletest): fix flake in Test_Runner/Cleanup | closed; merged | [@johnstcn](https://github.com/johnstcn) | ...ub.com/coder/coder/issues/10240 From the linked issue: - We get to the `require.Eventually` that asserts that the build was canceled - This times out after 10 seconds - It appears that the build job never got canceled after 10 seconds - It also appears that a second build never got created - We unfortunately appe... |
| [PR #11023](https://github.com/coder/coder/pull/11023) | PR | fix: pass in time parameter to prevent flakes | closed; merged | [@f0ssel](https://github.com/f0ssel) | ...ep:5:428 Here's what I have so far: - The tests failed very close to midnight: `insights_internal_test.go:162: now: 2023-11-08 23:59:56.781794 +0000 UTC m=+7.293516543` - I noticed the monotonic clock reading, ~~and upon further reading about it I think it's reasonable to strip this when dealing with parse fix: p... |
| [PR #11240](https://github.com/coder/coder/pull/11240) | PR | chore: fix flake, use time closer to actual test | closed; merged | [@Emyrk](https://github.com/Emyrk) | ... Fixes: https://github.com/coder/coder/issues/11011 Could reproduce by adding a sleep to the start of the test chore: fix flake, use time closer to actual test The tests were queued, and the autostart time was being set to the time the table was created, not when the test was actually being run. This diff was cau... |
| [PR #12377](https://github.com/coder/coder/pull/12377) | PR | chore: fix `Test_parseInsightsStartAndEndTime` flake | closed; merged | [@coadler](https://github.com/coadler) | chore: fix `Test_parseInsightsStartAndEndTime` flake Fixes https://github.com/coder/coder/issues/10600 chore: fix `Test_parseInsightsStartAndEndTime` flake Fixes https://github.com/coder/coder/issues/10600 chore: fix `Test_parseInsightsStartAndEndTime` flake Fixes https://github.com/coder/coder/issues/10600 coderd/i... |
| [PR #13453](https://github.com/coder/coder/pull/13453) | PR | chore: fix `TestServer/Prometheus/DBMetricsDisabled` test flake | closed; merged | [@coadler](https://github.com/coadler) | chore: fix `TestServer/Prometheus/DBMetricsDisabled` test flake See: https://github.com/coder/coder/actions/runs/9352137263/job/25739550487#step:5:368 chore: fix `TestServer/Prometheus/DBMetricsDisabled` test flake See: https://github.com/coder/coder/actions/runs/9352137263/job/25739550487#step:5:368 chore: fix `Tes... |
| [PR #13985](https://github.com/coder/coder/pull/13985) | PR | fix: address `TestPendingUpdatesMetric` flake | closed; merged | [@dannykopping](https://github.com/dannykopping) | ...lake Follow up of #13944 Changed the assertion in `TestPendingUpdatesMetric` to wait for the metric to be updated with the expected count of updates before proceeding; this should resolve test flakiness. fix: address `TestPendingUpdatesMetric` flake Follow up of #13944 Changed the assertion in `TestPendingUpdates... |
| [PR #17919](https://github.com/coder/coder/pull/17919) | PR | chore: fix flake on useAgentLogs | closed; merged | [@BrunoQuaresma](https://github.com/BrunoQuaresma) | chore: fix flake on useAgentLogs We need to wait for the result since the result is depending on effects. Fix https://github.com/coder/internal/issues/644 chore: fix flake on useAgentLogs We need to wait for the result since the result is depending on effects. Fix https://github.com/coder/internal/issues/644 chore:... |
| [PR #19450](https://github.com/coder/coder/pull/19450) | PR | fix: fix flake due to two time.Now() calls | closed; merged | [@bcpeinhardt](https://github.com/bcpeinhardt) | fix: fix flake due to two time.Now() calls fixes https://github.com/coder/internal/issues/559 This test is looking to see that after calling `coder schedule extend <workspace> 10h`, the scheduled stop time of the workspace is updated appropriately (or at least that the information printed to the terminal indicates t... |
| [PR #19478](https://github.com/coder/coder/pull/19478) | PR | fix: fix flake in TestExecutorAutostartSkipsWhenNoProvisionersAvailable | closed; merged | [@cstyan](https://github.com/cstyan) | ...enNoProvisionersAvailable The flake here had two causes: 1. related to usage of time.Now() in MustWaitForProvisionersAvailable and 2. the fact that UpdateProvisionerLastSeenAt can not use a time that is further in the past than the current LastSeenAt time Previously the test here was calling `coderdtest.MustWaitF... |
| [PR #19649](https://github.com/coder/coder/pull/19649) | PR | fix: fix TestExecutorAutostartSkipsWhenNoProvisionersAvailable flake, part 2 | closed; merged | [@cstyan](https://github.com/cstyan) | ...4#issuecomment-3237154735 The cause appears to be related to the assignment of `time.Now()` as the `LastSeenAt` time when creating a provisioner which can flake with the calculated scheduled next autostart and the code to set then `require.Eventually` the updated provisioner LastSeenAt. Instead we should simply c... |
| [PR #19654](https://github.com/coder/coder/pull/19654) | PR | test: fix flake, TestLabelsAggregation update & collect timing | closed; not_merged |  | test: fix flake, TestLabelsAggregation update & collect timing If you see the logs, the `collect` happens before the `update metrics` ``` t.go:106: 2025-08-30 11:43:03.849 [debu] prometheusmetrics: update metrics t.go:106: 2025-08-30 11:43:03.850 [debu] prometheusmetrics: collect metrics t.go:106: 2025-08-30 11:43:0... |
| [PR #19683](https://github.com/coder/coder/pull/19683) | PR | test: fix TestCache_DeploymentStats flake | closed; merged | [@ethanndickson](https://github.com/ethanndickson) | ...der/internal/issues/961 Likely the same deal as in #19599, the body of `require.Eventually` now fires immediately, when it used to fire after 250ms (the interval). Presumably, the deployment stats become ready before the vs code session count gets incremented. This was never an issue with the 250ms delay, as this... |
| [PR #20447](https://github.com/coder/coder/pull/20447) | PR | test: fix flake in TestAgent_Metrics_SSH | closed; merged | [@ethanndickson](https://github.com/ethanndickson) | test: fix flake in TestAgent_Metrics_SSH Closes https://github.com/coder/internal/issues/921 The flake in the linked issue was caused by the startup script taking longer than 1 second in CI. The existing conditional, that the startup script duration was under a second, was incorrect; the correct conditional is that... |
| [PR #21396](https://github.com/coder/coder/pull/21396) | PR | test: use deterministic time to avoid time-based flake | closed; merged | [@DanielleMaywood](https://github.com/DanielleMaywood) | test: use deterministic time to avoid time-based flake Fixes https://github.com/coder/internal/issues/1218 I managed to create a manual reproduction of the issue by slightly modifying the test to force `CreatedAt` to have the same value for multiple app status'. The fix works by using deterministic time for the test... |
| [PR #21981](https://github.com/coder/coder/pull/21981) | PR | chore: fix pty-max-limit flake | closed; not_merged |  | ...rately manage the same resources. If, as this PR is designed, we are willing to wait up to 30s to obtain a PTY if one is not immediately available, why not just retry with a short backoff (e.g. 1s)? @spikecurtis This approach was originally introduced by you and @mafredri : https://github.com/coder/internal/issue... |
| [PR #22639](https://github.com/coder/coder/pull/22639) | PR | fix(coderd): fix flaky TestGetUserStatusCounts timezone boundary | closed; merged | [@kylecarbs](https://github.com/kylecarbs) | ...tes its date range using the requested timezone/offset: ```go nextHourInLoc = dbtime.Now().Truncate(time.Hour).Add(time.Hour).In(loc) sixtyDaysAgo = dbtime.StartOfDay(nextHourInLoc).AddDate(0, 0, -60) ``` When the UTC time of day is earlier than the timezone offset (e.g. UTC 01:30 with offset `-2` means local tim... |
| [PR #22654](https://github.com/coder/coder/pull/22654) | PR | chore(cli): fix flaky temporal assertion in TestTokens | closed; merged | [@johnstcn](https://github.com/johnstcn) | chore(cli): fix flaky temporal assertion in TestTokens Fixes https://github.com/coder/internal/issues/1379 chore(cli): fix flaky temporal assertion in TestTokens Fixes https://github.com/coder/internal/issues/1379 chore(cli): fix flaky temporal assertion in TestTokens Fixes https://github.com/coder/internal/issues/1... |
| [PR #22740](https://github.com/coder/coder/pull/22740) | PR | fix(site): fix flaky TemplateVariablesPage submit test | closed; merged | [@kylecarbs](https://github.com/kylecarbs) | ...e submit test ## Root Cause The `createAndBuildTemplateVersion` mutation calls `waitBuildToBeFinished`, which polls `getTemplateVersion` behind a real `delay()` call: ```ts await delay(jobStatus === "pending" ? 250 : 1000); ``` On the first iteration, `jobStatus` is `undefined` (not `"pending"`), so the delay is... |
| [PR #23448](https://github.com/coder/coder/pull/23448) | PR | fix(coderd/x/chatd): stabilize auto-promotion flake | closed; merged | [@ibetitsmike](https://github.com/ibetitsmike) | ...InterruptAutoPromotionIgnoresLaterUsageLimitIncrease still relied on wall-clock polling after the acquire loop moved to a mock clock, so it could assert before chatd finished its asynchronous cleanup and auto-promotion work. Wait on explicit request-start signals and on the server's in-flight chat work before ass... |
| [PR #23655](https://github.com/coder/coder/pull/23655) | PR | fix(site/e2e): fix flaky updateTemplate test expecting transient URL | closed; merged | [@ethanndickson](https://github.com/ethanndickson) | ...er's index route (`<Navigate to="docs" replace />`). The assertion used `expect.poll()` with `toHavePathNameEndingWith(`/${name}`)`, which matches only the **transient intermediate URL** - it only exists while `Temp fix(site/e2e): fix flaky updateTemplate test expecting transient URL _PR generated by Mux but revi... |
| [PR #23816](https://github.com/coder/coder/pull/23816) | PR | fix: stabilize flaky chatd subscribe/promote queued tests | closed; merged | [@kylecarbs](https://github.com/kylecarbs) | ...diately. Even though `newTestServer` sets `PendingChatAcquireInterval: testutil.WaitLong` to prevent ticker-based polling, the wake channel bypasses this. This causes `processOnce` to acquire and process the chat concurrently with the fix: stabilize flaky chatd subscribe/promote queued tests ## Summary Fixes thre... |
| [PR #23830](https://github.com/coder/coder/pull/23830) | PR | fix: resolve TestScheduleOverride/extend flake caused by timezone hour boundary race | closed; merged | [@DanielleMaywood](https://github.com/DanielleMaywood) | ...n the CI runner's clock is near a UTC `:30` minute boundary. The test captured `time.Now()` before running the CLI command, then independently computed the expected deadline as `now + 10h` formatted in `Asia/Kolkata` (+05:30). The CLI `schedule extend` command internally calls its own `time.Now()` seconds-to-minu... |
| [PR #24240](https://github.com/coder/coder/pull/24240) | PR | fix: resolve idle timeout recording test flake on macOS | closed; merged | [@kylecarbs](https://github.com/kylecarbs) | ...en the next `Advance` is called, causing `"cannot advance ... beyond next timer/ticker event in 0s"`. 2. **The test depended on SIGINT being handled promptly.** After the `stop_timeout` timer was released, the test relied entirely on the shell process handling SIGINT (via `rec.done`). On macOS, `/bin/sh` may not... |
| [PR #24480](https://github.com/coder/coder/pull/24480) | PR | fix(site): fix flaky CreateWorkspacePage tests | closed; merged | [@DanielleMaywood](https://github.com/DanielleMaywood) | ...73. Three flaky/smelly patterns in `CreateWorkspacePage.test.tsx`: **Redundant `waitFor` around `userEvent` (internal#1472)** Most removed `waitFor` blocks wrapped only `userEvent.clear`/`type`/`click` with no assertion - `waitFor` resolves on the first pass when the callback doesn't throw, so these weren't causi... |
| [PR #24593](https://github.com/coder/coder/pull/24593) | PR | fix: fix flaky TestExpAgentsE2E/ExistingChatHistory | closed; not_merged |  | ...i-key`), producing an auth error that rendered an `error` banner in the TUI and polluted PTY output. Added a `chattest.NewOpenAI` mock so processing completes cleanly. 2. **Stable header match**: The PTY expect for `"direct open seed"` was racy because the mock's title fix: fix flaky TestExpAgentsE2E/ExistingChat... |
| [PR #24796](https://github.com/coder/coder/pull/24796) | PR | fix(site/e2e): backport verifyParameters flake fixes to 2.29 | closed; merged | [@f0ssel](https://github.com/f0ssel) | ...b.com/coder/coder/pull/24769). ## Root cause `verifyParameters` navigated with `waitUntil: "domcontentloaded"`, so the form rendered with the default parameter value (`"abc"`) from the React Query cache before the actual build parameter value (`"AAAAA"`) arrived fro fix(site/e2e): backport verifyParameters flake... |
| [PR #24949](https://github.com/coder/coder/pull/24949) | PR | fix(coderd/x/chatd/chaterror): de-flake TestClassify_ParsesRetryAfterHTTPDate | closed; not_merged |  | fix(coderd/x/chatd/chaterror): de-flake TestClassify_ParsesRetryAfterHTTPDate ## Problem `TestClassify_ParsesRetryAfterHTTPDate` flaked in CI ([run 25336190655](https://github.com/coder/coder/actions/runs/25336190655)): ``` --- FAIL: coderd/x/chatd/chaterror TestClassify_ParsesRetryAfterHTTPDate (0.00s) classify_tes... |
| [PR #25603](https://github.com/coder/coder/pull/25603) | PR | fix(coderd): fix flaky TestSendMessageWithModelOverrideUpdatesLastModelConfigID | closed; merged | [@johnstcn](https://github.com/johnstcn) | fix(coderd): fix flaky TestSendMessageWithModelOverrideUpdatesLastModelConfigID Fixes the flake in `TestSendMessageWithModelOverrideUpdatesLastModelConfigID` (and the same pattern in `TestSubsequentSendWithoutOverrideUsesPersistedModel`). ## Root Cause Both tests assert `require.Len(t, messages, 1)` immediately afte... |
| [PR #26199](https://github.com/coder/coder/pull/26199) | PR | test(scaletest/workspacetraffic): fix RPTY close flake on graceful timeout | closed; merged | [@jscottmiller](https://github.com/jscottmiller) | ...timeout ## Summary Fixes the `TestRun/RPTY` flake tracked in PLAT-116 (`timeout waiting for read to finish`). `rptyConn.Close` sends `Ctrl+C` to interrupt the command, then waits up to 30s for the read to finish. The read only unblocks once the server closes the reconnecting PTY stream, which depends on the agent... |

</details>
