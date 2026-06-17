# Database, transactions, migrations

DB-backed tests fail around shared Postgres resources, cleanup gaps, socket leaks, transaction timing, migrations, and DB-backed async state.

## Count

| references | issues | PRs |
| ---: | ---: | ---: |
| 47 | 15 | 32 |

## Why it flakes

Postgres amplifies timing and isolation mistakes. The failure often looks like a product assertion, but the cause is shared test infrastructure.

## Common fixes

- Create isolated DB resources per test where practical.
- Clean up one-shot DBs, sockets, listeners, and rows explicitly.
- Use direct DB setup only when API-level setup introduces unrelated async races.
- Cap DB-heavy package parallelism separately from pure unit tests.
- Avoid exact timestamp equality after database round trips.

## Code examples

These examples are illustrative patterns for the category, not direct patches against one specific test.

<details>
<summary>Code examples</summary>

### Bad: share mutable DB rows across parallel tests

```go
user := dbgen.User(t, db, database.User{})

t.Run("first", func(t *testing.T) {
	t.Parallel()
	require.NoError(t, db.UpdateUser(ctx, user.ID, patchA))
})
t.Run("second", func(t *testing.T) {
	t.Parallel()
	require.NoError(t, db.UpdateUser(ctx, user.ID, patchB))
})
```

### Better: create isolated DB resources per subtest

```go
for _, tc := range cases {
	tc := tc
	t.Run(tc.name, func(t *testing.T) {
		t.Parallel()
		user := dbgen.User(t, db, database.User{
			Email: testutil.GetRandomName(t) + "@example.com",
		})
		require.NoError(t, db.UpdateUser(ctx, user.ID, tc.patch))
	})
}
```

</details>

## Suggested first slice

Inventory DB-heavy flaky packages and split their parallelism profile from cheap unit tests.

<details>
<summary>References (47)</summary>

| ref | type | title | status | evidence |
| --- | --- | --- | --- | --- |
| [issue #388](https://github.com/coder/coder/issues/388) | issue | Investigate test flake for allocating ports with PostgreSQL Docker | closed; linked_fix_merged | Investigate test flake for allocating ports with PostgreSQL Docker https://github.com/coder/coder/runs/5375197003?check_suite_focus=true#step:9:52 Investigate test flake for allocating ports with PostgreSQL Docker https://github.com/coder/coder/runs/5375197003?check_suite_focus=true#step:9:52 PR #389: test: Add mute... |
| [issue #2347](https://github.com/coder/coder/issues/2347) | issue | CI test/go/postgres is flaky | closed; linked_fix_merged | CI test/go/postgres is flaky these tests are timing out en-mass on many runs, e.g. https://github.com/coder/coder/actions/runs/2502674150/attempts/2 Need to investigate, but some possible issues: * we set parallel=1 and timeout=5m --- are these tests just taking too long? * are any postgres workers getting OOM kille... |
| [issue #6197](https://github.com/coder/coder/issues/6197) | issue | chore: test flake: TestTemplateVersionDryRun/OK | closed | ...``` Unable to reproduce locally. Ran test 100 times with race detector on with `DB=ci`. chore: test flake: TestTemplateVersionDryRun/OK Seen here: https://github.com/coder/coder/actions/runs/4172299609/jobs/7223229286 ``` templateversions_test.go:713: Error Trace: /home/runner/work/coder/coder/coderd/templatevers... |
| [issue #10219](https://github.com/coder/coder/issues/10219) | issue | test flake: TestServerDBCrypt | closed | test flake: TestServerDBCrypt **Test execution link**: [TestServerDBCrypt](https://app.datadoghq.com/ci/test/AgAAAYsCC68gAnzXGQAAAAAAAAAYAAAAAEFZc0NDNjhnQUFDUFVBcjRkY1ZRcEZaOQAAACQAAAAAMDE4YjAyMGMtOWYyYS00ZjQ3LWFhN2ItMmU2MzM3ZGJmNjli) **Service**: coder **Branch**: [main](https://app.datadoghq.com/ci/test-branch/git... |
| [issue #11229](https://github.com/coder/coder/issues/11229) | issue | flake: ci: potential race condition in make gen | closed | ...rated.ts 2426ms 2023-12-15T10:04:45.2364760Z # github.com/coder/coder/v2/coderd/database 2023-12-15T10:04:45.2400525Z ##[error]coderd/database/queries.sql.go:73:16: undefined: time 2023-12-15T10:04:45.2405154Z ##[error]coderd/database/queries.sql.go:74:16: undefined: uuid 2023-12-15T10:04:45.2406082Z ##[error]cod... |
| [issue #11576](https://github.com/coder/coder/issues/11576) | issue | flake: TestPubsub/ClosePropagatesContextCancellationToSubscription | closed | .../coder/actions/runs/7489417059/job/20385945806) ``` === Failed === FAIL: coderd/database/pubsub TestPubsub/ClosePropagatesContextCancellationToSubscription (3.93s) pubsub_test.go:152: Error Trace: /home/runner/actions-runner/_work/coder/coder/coderd/database/pubsub/pubsub_test.go:152 Error: Received unexpected er... |
| [issue #12030](https://github.com/coder/coder/issues/12030) | issue | test flake: TestWatchdog_Timeout | closed | ...r/coder/actions/runs/7801997439/job/21278471914 ``` === Failed === FAIL: coderd/database/pubsub TestWatchdog_Timeout (10.00s) t.go:99: 2024-02-06 15:26:26.334 [debu] context done; exiting publishLoop t.go:99: 2024-02-06 15:26:26.334 [debu] context done; exiting subscribeMonitor watchdog_test.go:85: timeout ``` te... |
| [issue #12529](https://github.com/coder/coder/issues/12529) | issue | flake: coderd/database/dbpurge TestDeleteOldProvisionerDaemons | closed | flake: coderd/database/dbpurge TestDeleteOldProvisionerDaemons https://github.com/coder/coder/actions/runs/8231926826/job/22509574243?pr=12517#step:5:331 ``` === FAIL: coderd/database/dbpurge TestDeleteOldProvisionerDaemons (10.09s) t.go:99: 2024-03-11 11:59:45.970 [info] pubsub: pubsub dialing postgres network=tcp... |
| [issue #12932](https://github.com/coder/coder/issues/12932) | issue | test flake: enterprise/coderd TestEntitlements/FullLicense | closed | ...d coordinator delete coordinator_id=61203490-ef90-48e4-a7c2-1fa681311603 error="sql: database is closed" *** slogtest: log detected at level ERROR; TEST FAILURE *** t.go:99: 2024-04-10 19:33:07.339 [debu] coderd.pgcoord: ending cleanupLoop coordinator_id=61203490-ef90-48e4-a7c2-1fa681311603 error="context cancele... |
| [issue #13165](https://github.com/coder/coder/issues/13165) | issue | Test flake: `coderd/database/dbpurge TestDeleteOldWorkspaceAgentStats` | closed | Test flake: `coderd/database/dbpurge TestDeleteOldWorkspaceAgentStats` https://github.com/coder/coder/actions/runs/8964016459/job/24615155790?pr=13164 Test flake: `coderd/database/dbpurge TestDeleteOldWorkspaceAgentStats` https://github.com/coder/coder/actions/runs/8964016459/job/24615155790?pr=13164 cc @mafredri si... |
| [issue #13293](https://github.com/coder/coder/issues/13293) | issue | flake: coderd/database/pubsub TestMeasureLatency/MeasureLatencyRecvTimeout | closed | flake: coderd/database/pubsub TestMeasureLatency/MeasureLatencyRecvTimeout Seen here: https://github.com/coder/coder/actions/runs/9111846804/job/25049919786?pr=13292#step:5:381 ``` === FAIL: coderd/database/pubsub TestMeasureLatency/MeasureLatencyRecvTimeout (6.24s) t.go:99: 2024-05-16 12:08:36.496 [debu] performing... |
| [issue #13430](https://github.com/coder/coder/issues/13430) | issue | test flake: `TestDeleteOldWorkspaceAgentStats` | closed | ..._test.go:123: Error Trace: /home/runner/actions-runner/_work/coder/coder/coderd/database/dbpurge/dbpurge_test.go:123 Error: Condition never satisfied Test: TestDeleteOldWorkspaceAgentStats Messages: it should delete old stats: [] ``` test flake: `TestDeleteOldWorkspaceAgentStats` Slack context: https://codercom.s... |
| [issue #13801](https://github.com/coder/coder/issues/13801) | issue | flake: `AgentHasNotConnectedSinceWeek_LogsExpired` | closed | ...ctions/runs/9836445062/job/27152170089?pr=13799 ``` === Failed === FAIL: coderd/database/dbpurge TestDeleteOldWorkspaceAgentLogs/AgentHasNotConnectedSinceWeek_LogsExpired (10.02s) dbpurge_test.go:191: Error Trace: /home/runner/work/coder/coder/coderd/database/dbpurge/dbpurge_test.go:191 Error: Condition never sat... |
| [issue #14035](https://github.com/coder/coder/issues/14035) | issue | flake: TestUserLatencyInsights | closed | ...0a9-bff6-2b1ac4548b90 ... error= fetch object: github.com/coder/coder/v2/coderd/database/dbauthz.(*querier).GetTemplateByID.fetch[...].func1 /home/run flake: TestUserLatencyInsights seen here: https://github.com/coder/coder/actions/runs/9962871701/job/27528080557 ``` t.go:108: 2024-07-16 19:37:42.000 [erro] works... |
| [issue #15073](https://github.com/coder/coder/issues/15073) | issue | flake: TestWorkspaceBuildTimings | closed | ...workspacebuilds_test.go:1233: Error Trace: /home/runner/work/coder/coder/coderd/database/dbgen/dbgen.go:297 /home/runner/work/coder/coder/coderd/workspacebuilds_test.go:1233 /home/runner/work/coder/coder/coderd/workspacebuilds_test.go:1302 Error: Received unexpected error: execute transaction: github.com/coder/co... |
| [PR #389](https://github.com/coder/coder/pull/389) | PR | test: Add mutex to opening PostgreSQL ports to prevent collision | closed; merged | test: Add mutex to opening PostgreSQL ports to prevent collision Closes #388. test: Add mutex to opening PostgreSQL ports to prevent collision Closes #388. test: Add mutex to opening PostgreSQL ports to prevent collision Closes #388. database/postgres/postgres.go # [Codecov](https://codecov.io/gh/coder/coder/pull/38... |
| [PR #1002](https://github.com/coder/coder/pull/1002) | PR | fix: Agent/SessionTTY flake waiting for terminal prompt | closed; merged | ...Coverage Δ \| \| \|---\|---\|---\| \| unittest-go-macos-latest \| `?` \| \| \| unittest-go-postgres- \| `?` \| \| \| unittest-go-ubuntu-latest \| `56.55% <ø> (+0.05%)` \| :arrow_up: \| \| unittest-js \| `?` \| \| \| [Impacted Files](https://codecov.io/gh/coder/coder/pull/1002?src=pr&el=tree&utm_medium=referral&ut... |
| [PR #1643](https://github.com/coder/coder/pull/1643) | PR | chore: skip some flaky tests | closed; merged | ..._test.go coderd/workspaces_test.go peer/conn_test.go It looks like the `test/go/postgres` check is flaking out in this PR too 😢 . I'm not sure if the suppression here were for that or other tests. I hope we can use a similar tactic to hunt down the flakes in that check, or at least only run it when the data layer... |
| [PR #2413](https://github.com/coder/coder/pull/2413) | PR | Fix socket leak, clean up single use postgres databases | closed; merged | Fix socket leak, clean up single use postgres databases First PR for #2347 This fixes up a socket leak in our use of Migrate. It also introduces cleanup of single-use databases in postgres, since the postgres container outlives the test run, if we don't clean up these databases the container will continue to grow in... |
| [PR #6482](https://github.com/coder/coder/pull/6482) | PR | chore: fix coordinator flake by moving pubsub below register | closed; merged | ...below register After making the in-memory pubsub conform to the expectations of PostgreSQL, this flake started appearing. This fixes it because the agent socket is registered when a message is received. chore: fix coordinator flake by moving pubsub below register After making the in-memory pubsub conform to the e... |
| [PR #8369](https://github.com/coder/coder/pull/8369) | PR | chore(coderd/database): fix test flake in TestUserLastSeenFilter | closed; merged | chore(coderd/database): fix test flake in TestUserLastSeenFilter chore(coderd/database): fix test flake in TestUserLastSeenFilter chore(coderd/database): fix test flake in TestUserLastSeenFilter coderd/database/querier_test.go |
| [PR #10222](https://github.com/coder/coder/pull/10222) | PR | chore(enterprise/cli): fix test flake in TestServerDBCrypt | closed; merged | chore(enterprise/cli): fix test flake in TestServerDBCrypt Fixes https://github.com/coder/coder/issues/10219 chore(enterprise/cli): fix test flake in TestServerDBCrypt Fixes https://github.com/coder/coder/issues/10219 chore(enterprise/cli): fix test flake in TestServerDBCrypt Fixes https://github.com/coder/coder/iss... |
| [PR #10992](https://github.com/coder/coder/pull/10992) | PR | fix: use database for user creation to prevent flake | closed; merged | fix: use database for user creation to prevent flake After speaking with @Emyrk I moved the user creation of these tests to use the database directly to speed things up and do less http requests in order to stay under the 50 second timeout. Closes https://github.com/coder/coder/issues/10978 fix: use database for use... |
| [PR #11384](https://github.com/coder/coder/pull/11384) | PR | chore(coderd/database/dbfake): fix pq test flake in TestStart_Starting | closed; merged | chore(coderd/database/dbfake): fix pq test flake in TestStart_Starting test-go-pg got skipped in https://github.com/coder/coder/pull/11381 so [this](https://github.com/coder/coder/actions/runs/7395536966/job/20118913609#step:5:331) snuck through. ``` start_test.go:423: Error Trace: /home/runner/actions-runner/_work/... |
| [PR #12517](https://github.com/coder/coder/pull/12517) | PR | test(coderd): skip flaky dau test | closed; merged | ...eries are replaced by insights queries, disabling for now. Closes #12509 coderd/database/dbpurge/dbpurge_test.go coderd/insights_test.go > @johnstcn pointed out this test may be failing due to a timezone issue following a recent DST change; I'm happy to try fix it in the interim if needed I figured that might be... |
| [PR #12700](https://github.com/coder/coder/pull/12700) | PR | chore(coderd/workspaceapps/apptest): fix test flake due to concurrent usage of same deployment | closed; merged | ...art to ProxySubdomain tests. coderd/workspaceapps/apptest/apptest.go ``` create db with template: github.com/coder/coder/v2/coderd/database/postgres.Open /home/runner/actions-runner/_work/coder/coder/coderd/database/postgres/postgres.go:41 - pq: could not write to file "base/35912/17659": No space left on device... |
| [PR #13301](https://github.com/coder/coder/pull/13301) | PR | chore: fix `TestMeasureLatency/MeasureLatencyRecvTimeout` flake | closed; merged | ...chore: fix `TestMeasureLatency/MeasureLatencyRecvTimeout` flake Makefile coderd/database/pubsub/psmock/doc.go coderd/database/pubsub/psmock/psmock.go coderd/database/pubsub/pubsub_linux_test.go * **#13301** <a href="https://app.graphite.dev/github/pr/coder/coder/13301?utm_source=stack-comment-icon" target="_blank... |
| [PR #13431](https://github.com/coder/coder/pull/13431) | PR | chore: skip `TestDeleteOldWorkspaceAgentStats` due to flaking | closed; not_merged | ...to flaking chore: skip `TestDeleteOldWorkspaceAgentStats` due to flaking coderd/database/dbpurge/dbpurge_test.go * **#13431** <a href="https://app.graphite.dev/github/pr/coder/coder/13431?utm_source=stack-comment-icon" target="_blank"><img src="https://static.graphite.dev/graphite-32x32-black.png" alt="Graphite"... |
| [PR #14634](https://github.com/coder/coder/pull/14634) | PR | fix: fix TestPing/1Ping flake | closed; merged | fix: fix TestPing/1Ping flake Fixes #14632. With Postgres enabled, this test can run slow enough that a direct connection can't be established before the test times out. We just want to see that the ping command finished, so we'll accept confirmation of either a DERP or p2p connection. fix: fix TestPing/1Ping flake... |
| [PR #15314](https://github.com/coder/coder/pull/15314) | PR | fix: create contexts per sub-test to fix flake | closed; merged | ...ob/32371950701 https://coder.com/blog/go-testing-contexts-and-t-parallel coderd/database/querier_test.go * **#15314** <a href="https://app.graphite.dev/github/pr/coder/coder/15314?utm_source=stack-comment-icon" target="_blank"><img src="https://static.graphite.dev/graphite-32x32-black.png" alt="Graphite" width="1... |
| [PR #15629](https://github.com/coder/coder/pull/15629) | PR | chore: fix more flaky tests on Windows with Postgres | closed; merged | chore: fix more flaky tests on Windows with Postgres Addresses the following flakes: - https://github.com/coder/internal/issues/222 - https://github.com/coder/internal/issues/223 - https://github.com/coder/internal/issues/224 - https://github.com/coder/internal/issues/225 - https://github.com/coder/internal/issues/2... |
| [PR #16773](https://github.com/coder/coder/pull/16773) | PR | fix: use `dbtime` in `dbmem` query to fix flake | closed; merged | ...ding applied by `dbtime`. `dbtime` was used on the timestamps inserted into the DB, but not within the query. Once using `dbtime` within the query there were no failures in 200 runs. fix: use `dbtime` in `dbmem` query to fix flake Closes https://github.com/coder/internal/issues/447. The test was failing 30% of th... |
| [PR #16799](https://github.com/coder/coder/pull/16799) | PR | test: fix flaky tests | closed; merged | ...ernal/issues/451 Create separate context with timeout for every subtest. coderd/database/querier_test.go |
| [PR #18246](https://github.com/coder/coder/pull/18246) | PR | fix(cli): fix flakes related to context cancellation when establishing pg connections | closed; merged | ...github.com/coder/coder/pull/18195 was merged, we started running CLI tests with postgres instead of just dbmem. This surfaced errors related to context cancellation while establishing postgres connections. This PR should fix https://github.com/coder/internal/issues/672. Related to https://github.com/coder/coder/i... |
| [PR #18441](https://github.com/coder/coder/pull/18441) | PR | fix: fix TestAcquireJobWithCancel_Cancel flake | closed; merged | ... was failing because it was checking for context.Canceled using xerrors.Is, but postgres returns a different error ("pq: canceling statement due to user request") when a query is cancelled. This change uses database.IsQueryCanceledError which properly handles both context.Canceled and postgres-specific cancellati... |
| [PR #18932](https://github.com/coder/coder/pull/18932) | PR | fix(coderd): fix flake in `TestAPI/ModifyAutostopWithRunningWorkspace` | closed; merged | ...rovisioner job from _after_ it completed. Let me demonstrate: Here we query the database for `database.WorkspaceBuild`. https://github.com/coder/coder/blob/a3f64f74f794c733126ad21cd1feb0801caf67c4/coderd/coderd.go#L1409-L1415 Inside of the `workspaceBuild` route handler, we call `workspaceBuildsData` https://gith... |
| [PR #19029](https://github.com/coder/coder/pull/19029) | PR | test(coderd/database): use seperate context for subtests to fix flake | closed; merged | test(coderd/database): use seperate context for subtests to fix flake Fixes flakes like https://github.com/coder/coder/actions/runs/16487670478/job/46615625141, caused by the issue described in https://coder.com/blog/go-testing-contexts-and-t-parallel It'd be cool if we could lint for this? That a context from an ou... |
| [PR #19330](https://github.com/coder/coder/pull/19330) | PR | test(coderd/database): use seperate context for subtests to fix flake | closed; merged | test(coderd/database): use seperate context for subtests to fix flake Fixes flakes like https://github.com/coder/coder/actions/runs/16927282256/job/47965470039 https://coder.com/blog/go-testing-contexts-and-t-parallel ...I'm going to take a stab at turning this into a lint rule. I think it's possible by just reading... |
| [PR #19494](https://github.com/coder/coder/pull/19494) | PR | chore: add flake detection on prs | closed; not_merged | ...un JSON artifact. Includes permissions, concurrency, hardened runner usage, and Postgres startup. \| \| **Tests: Random failure injection**<br>`cli/agent_test.go` \| Introduces a 10% probabilistic `t.Fatal("Random test failure for testing purposes")` in the `TestWorkspaceAgent` LogDirectory subtest and imports `m... |
| [PR #19723](https://github.com/coder/coder/pull/19723) | PR | ci(scripts/flakecheck): add AST-based flake detection for modified Go tests | closed; not_merged | ...or N times with `go test -json` to detect flakes. - Default repeat count is 10; DB-friendly defaults: `-p 4 -parallel 4`. - Output is suppressed for stable tests; prints only flaky or broken selectors with fail counts. Exits non-zero on any flake or broken test. - Makefile: add `test-flakes` target which depends... |
| [PR #21233](https://github.com/coder/coder/pull/21233) | PR | fix(coderd/database): sort template version variables and fix test flake | closed; merged | fix(coderd/database): sort template version variables and fix test flake Previously the GetTemplateVersionVariables query did not sort output, relying on PostgreSQL on-disk ordering which is undeterministic. Variables are now sorted by name because there is no alternative for ordering. Tests were adjusted to accommo... |
| [PR #22910](https://github.com/coder/coder/pull/22910) | PR | fix: increase migration lock timeout to prevent flaky parallel test | closed; merged | fix: increase migration lock timeout to prevent flaky parallel test ## Problem `TestMigrate/Parallel` flakes with: ``` timeout: can't acquire database lock ``` ## Root Cause The test runs two concurrent `migrations.Up(db)` calls on the same database. golang-migrate wraps every `Lock()` call with a [15-second timeout... |
| [PR #23147](https://github.com/coder/coder/pull/23147) | PR | fix(cored): fix flaky TestInterruptAutoPromotionIgnoresLaterUsageLimitIncrease | closed; merged | ...t_queued_messages` (the auto-promotion requires multiple goroutine switches and DB transactions that cannot complete between two consecutive synchronous calls). The `len(existingQueued) > 0` condition reliably triggers queueing regardless of chat status. Passes 25/25 with `-count=25`. fix(cored): fix flaky TestIn... |
| [PR #24066](https://github.com/coder/coder/pull/24066) | PR | fix(coderd/x/chatd): fix flaky TestAwaitSubagentCompletion/CompletesViaPubsub | closed; merged | ...he processor publishes notifications on `ChatStreamNotifyChannel(child.ID)` via PostgreSQL `LISTEN/NOTIFY`. After `drainInflight()` returns, these stale notifications can still be buffered in the pgListener's `NotifyChan()`. When `awaitSubagentCompletion` subscribes and a stale notification is dispatched between... |
| [PR #24108](https://github.com/coder/coder/pull/24108) | PR | fix(enterprise/coderd/x/chatd): harden TestSubscribeRelayEstablishedMidStream against CI flakes | closed; merged | ...worker pipeline (model resolution, message loading, LLM call) involves multiple DB round-trips that can be slow when PostgreSQL is shared with many parallel test packages. 3. **Add a status-polling loop while waiting for the streaming request.** If the worker errors out during chat processing, the test now fails... |
| [PR #24666](https://github.com/coder/coder/pull/24666) | PR | fix(coderd/x/chatd): fix flaky TestSpawnComputerUseAgentInheritsContext | closed; merged | ...entInheritsContext`. - The test inserts an Anthropic provider directly into the DB after `CreateChat` has already been called - The server's background goroutine may have already cached the provider list (OpenAI only) via `configCache.EnabledProviders()` with a 10s TTL - The direct DB insert bypasses the pubsub e... |
| [PR #25306](https://github.com/coder/coder/pull/25306) | PR | fix(coderd): stabilize TestPatchChatMessage/ChangesModel flaky test | closed; merged | ...de) while the first processing round is still running. The `InsertChatMessages` SQL CTE unconditionally updates `chats.last_model_config_id` to the model of the last inserted message. When t fix(coderd): stabilize TestPatchChatMessage/ChangesModel flaky test Fixes coder/internal#1535 ## Problem `TestPatchChatMess... |

</details>
