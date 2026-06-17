# Resource exhaustion and timeouts

Slow runners, CPU pressure, memory pressure, PTY exhaustion, OOMs, and overloaded parallel jobs show up as nondeterministic timeouts.

## Count

| references | issues | PRs |
| ---: | ---: | ---: |
| 21 | 14 | 7 |

## Why it flakes

A timeout is a symptom, not a root cause. Without runner and package fanout data, teams usually guess.

## Common fixes

- Log runner CPU, memory, job name, package, and parallelism in failure output.
- Cap Postgres, PTY, browser, and network-heavy packages separately from cheap tests.
- Avoid blanket timeout increases unless the product actually depends on wall-clock elapsed time.
- Separate resource-sensitive stress runs from normal PR checks.
- Track rerun minutes consumed by known flaky signatures.

## Code examples

These examples are illustrative patterns for the category, not direct patches against one specific test.

<details>
<summary>Code examples</summary>

### Bad: unbounded parallel work inside an already parallel package

```go
for _, workspace := range workspaces {
	workspace := workspace
	go func() {
		_ = startWorkspace(ctx, workspace)
	}()
}
```

### Better: bound fanout and join before cleanup

```go
group, ctx := errgroup.WithContext(ctx)
group.SetLimit(4)

for _, workspace := range workspaces {
	workspace := workspace
	group.Go(func() error {
		return startWorkspace(ctx, workspace)
	})
}

require.NoError(t, group.Wait())
```

</details>

## Suggested first slice

Measure package fanout for the highest timeout buckets and tune parallelism by package class.

<details>
<summary>References (21)</summary>

| ref | type | title | status | evidence |
| --- | --- | --- | --- | --- |
| [issue #2335](https://github.com/coder/coder/issues/2335) | issue | test flake: coderd/devtunnel TestTunnel | closed; linked_fix_merged | ...890362136?check_suite_focus=true#step:10:76)-144da60e49d9.wg-tunnel.coder.app": context deadline exceeded (Client.T test flake: coderd/devtunnel TestTunnel c.f. https://github.com/coder/coder/actions/runs/2498710623/attempts/1 ``` === FAIL: coderd/devtunnel TestTunnel (159.50s) tunnel_test.go:47: https://fcca5909... |
| [issue #5187](https://github.com/coder/coder/issues/5187) | issue | Flaky: loadtest/reconnectingpty | closed | Flaky: loadtest/reconnectingpty I'm not able to pass CI tests and simply burning CPU cycles on this test: ``` "error": connection closed storj.io/drpc/drpcstream.(*Stream).sendPacket:268 storj.io/drpc/drpcstream.(*Stream).CloseSend:501 storj.io/drpc/drpcserver.(*Server).handleRPC:126 storj.io/drpc/drpcserver.(*Serve... |
| [issue #5343](https://github.com/coder/coder/issues/5343) | issue | flaky: TestWorkspaceAppsNonCanonicalHeaders | closed | ...et "http://localhost:50992/@me/adoring-dirac1/apps/test-app-owner/?query=true": context deadline exceeded Test: TestWorkspaceAppsNonCanonicalHeaders/ProxyPath t.go:81: 2022-12-08 05:34:58.441 [WARN] <github.com/coder/coder/coderd/httpmw/logger.go:63> Logger.func1.1.1 GET flaky: TestWorkspaceAppsNonCanonicalHeader... |
| [issue #8968](https://github.com/coder/coder/issues/8968) | issue | test flake: coderd TestWorkspaceWatcher | closed | ...e/runner/actions-runner/_work/coder/coder/coderd/workspaces_test.go:2200 Error: timed out waiting for event Test: TestWorkspaceWatcher Messages: workspace build faile test flake: coderd TestWorkspaceWatcher c.f. https://github.com/coder/coder/actions/runs/5797085582/job/15711945289?pr=8939 ``` t.go:85: 2023-08-08... |
| [issue #9315](https://github.com/coder/coder/issues/9315) | issue | flake: TestDERPHeaders | closed | ...:39.3404118Z Test: TestDERPHeaders 2023-08-24T18:30:39.3405131Z Messages: match deadline exceeded: context deadline exceeded (wanted "pong from epic-goodall9-MpM"; got "ping to \"epic-goodall9-MpM\" timed out \r\n") 2023-08-24T18:30:39.3405770Z ptytest.go:95: 2023-08-24 18:29:28.810: cmd: closing expecter: PTY cl... |
| [issue #9400](https://github.com/coder/coder/issues/9400) | issue | test flake TestWorkspace/Rename | closed | ...two dashes as a special sequence in DevURLs? Anyway, when the workspace name is too long, we trim it down, but sometimes the trimming can leave a `-` at the end, which we then add `-test` to, and validation fails. |
| [issue #9744](https://github.com/coder/coder/issues/9744) | issue | test flake: TestWorkspaceAgentTailnetDirectDisabled | closed | ...oder/coder/coderd/workspaceagents_test.go:708 Error: Received unexpected error: context deadline exceeded Test: TestWorkspaceAgentTailnetDirectDisabled ``` https://github.com/coder/coder/actions/runs/6220659445/job/16881112433?pr=9717 test flake: TestWorkspaceAgentTailnetDirectDisabled ``` workspaceagents_test.go... |
| [issue #10978](https://github.com/coder/coder/issues/10978) | issue | flake: TestPaginatedUsers | closed | ...expected error: Get "http://localhost:38403/api/v2/users?limit=5&offset=20&q=": context deadline exceeded Test: TestPaginatedUsers/all_users_5 Messages: prev page === FAIL: coderd TestPaginatedUsers/username_search_3#01 (50.00s) user flake: TestPaginatedUsers ``` === Failed === FAIL: coderd TestPaginatedUsers/all... |
| [issue #11389](https://github.com/coder/coder/issues/11389) | issue | test flake: TestStart_Starting | closed | ...li/start_test.go:438 Error: read error Test: TestStart_Starting Messages: match deadline exceeded: context deadline exceeded (wanted "workspace has been started"; got ".\r\n==> ⧗ Queued\r\n=== ✔ Queued [0ms]\r\n==> ⧗ Running\r\n") ``` |
| [issue #11507](https://github.com/coder/coder/issues/11507) | issue | flake: TestSSH/Stdio_RemoteForward_Signal | closed | ...ui.Agent /home/runner/actions-runner/_work/coder/coder/cli/cliui/agent.go:108 - context deadline exceeded ssh_test.go:305: Error Trace: /home/runner/actions-runner/_work/coder/coder/cli/ssh_test.go:305 /home/runner/actions-runner/_work/coder/coder/cli/ssh_test.go:1057 /opt/hostedtoolcache/go/1.21.5/x64/src/runtim... |
| [issue #11735](https://github.com/coder/coder/issues/11735) | issue | flake: scaletest/workspacetraffic TestRun/App | closed | ... get reader: received close frame: status = StatusPolicyViolation and reason = "timed out" run_test.go:356: read errors: 0 run_test.go:357: write errors: 0 run_test.go:358: bytes read total: 1024 run_test.go:359: bytes written total: 1024 ``` Seen here: https://github.com/coder/coder/runs/20716735726 flake: scale... |
| [issue #12603](https://github.com/coder/coder/issues/12603) | issue | flake: TestExecutorAutostartUserSuspended | closed | ...alhost:45405/api/v2/users/196c182b-8400-40dd-8cf0-47f2152f174e/status/suspend": context deadline exceeded Test: TestExecutorAutostartUserSuspended Messages: update user status ``` flake: TestExecutorAutostartUserSuspended Seen [here](https://github.com/coder/coder/actions/runs/8289507869/job/22686061079) ``` life... |
| [issue #13943](https://github.com/coder/coder/issues/13943) | issue | flake: `TestPendingUpdatesMetric` | closed | ...oder/coderd/notifications/metrics_test.go:266 Error: Received unexpected error: context deadline exceeded Test: TestPendingUpdatesMetric ``` |
| [issue #15782](https://github.com/coder/coder/issues/15782) | issue | flake: `TestPGCoordinatorSingle_MissedHeartbeats_NoDrop` | closed | ...oder/actions/runs/12230347616/job/34112326592?pr=15771 ``` pgcoord_test.go:959: context deadline exceeded pgcoord_test.go:376: Error Trace: C:/a/coder/coder/enterprise/tailnet/pgcoord_test.go:953 C:/a/coder/coder/enterprise/tailnet/pgcoord_test.go:972 C:/a/coder/coder/enterprise/tailnet/pgcoord_test.go:376 Error:... |
| [PR #9928](https://github.com/coder/coder/pull/9928) | PR | test: fix flaky TestCreateValidateRichParameters/ValidateString | closed; merged | ...[a-z]+$\")" create_test.go:448: 2023-09-27 16:54:58.779: cmd: read error: match deadline exceeded: context deadline exceeded (wanted "Confirm create?"; got " (default: \"\"): can't validate build parameter \"string_parameter\": this is error (value \"\" does not match \"^[a-z]+$\")\n> Enter a value (default: \"\"... |
| [PR #10066](https://github.com/coder/coder/pull/10066) | PR | chore: increase `ForceCancelInterval` for test flakes | closed; merged | chore: increase `ForceCancelInterval` for test flakes See https://github.com/coder/coder/actions/runs/6411239320/job/17406394658 chore: increase `ForceCancelInterval` for test flakes See https://github.com/coder/coder/actions/runs/6411239320/job/17406394658 chore: increase `ForceCancelInterval` for test flakes See h... |
| [PR #12364](https://github.com/coder/coder/pull/12364) | PR | fix(cli): address test flake in TestSSH/Stdio_StartStoppedWorkspace_CleanStdout | closed; not_merged | ...ssh_test.go From inspecting the test output more, it looks like this was just a context deadline exceeded. I'm still running into flakes for this test, does this PR fix it or do we need an alternate fix? (See: https://github.com/coder/coder/actions/runs/8420752158/job/23056129504?pr=12675) Yeah I just ran into th... |
| [PR #13250](https://github.com/coder/coder/pull/13250) | PR | fix: update tests for useClipboard to minimize risks of flakes | closed; merged | ...Changes made - Updated all test setup/teardown logic to avoid mishaps with mock timeouts, and also to increase test isolation - Updated test approach to use `describe.each` to improve test isolation between HTTPS and HTTP-only test cases - Updated how mock clipboard was defined - Added extra test cases for checki... |
| [PR #18872](https://github.com/coder/coder/pull/18872) | PR | fix(cli): scope context per subtest to fix flake test in prebuilt workspace delete | closed; merged | ...reated at the top level. Since the subtests run in parallel, they could run for too long and cause the shared context to expire. This sometimes led to context deadline exceeded errors, especially during the `testutil.Eventually` check for running prebuilt workspaces. The fix is to create a fresh context per s fix... |
| [PR #22883](https://github.com/coder/coder/pull/22883) | PR | test(cli): fix flaky TestGitSSH/Local_SSH_Keys on Windows CI | closed; merged | ...indows CI The `TestGitSSH/Local_SSH_Keys` test was flaking on Windows CI with a context deadline exceeded error when calling `client.GitSSHKey(ctx)`. Two issues contributed to the flake: 1. `prepareTestGitSSH` called `coderdtest.AwaitWorkspaceAgents` without passing the caller's context. This created a separate i... |
| [PR #26009](https://github.com/coder/coder/pull/26009) | PR | ci: reduce flake-go parallelism to fit 4-vCPU runner | closed; not_merged | ...rallelism-tests=16`, the worst-case concurrency is 64 in-flight subtests, which OOMed the runner on PRs whose `whichtests` selection covered `./cli` and `./enterprise/cli` at the same time. Concrete example: run [26845700051](https://github.com/coder/coder/actions/runs/26845700051) peaked at 14.8 / 16 GB and the... |

</details>
