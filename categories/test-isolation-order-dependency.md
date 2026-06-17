# Test isolation and order dependency

Tests leak state through temp dirs, caches, duplicate names, reused ports, contexts, cleanup gaps, random order, or parallel subtests.

## Count

| references | issues | PRs |
| ---: | ---: | ---: |
| 20 | 5 | 15 |

## Why it flakes

These failures are preventable. The suite should not depend on test order or shared global state unless the test says so explicitly.

## Common fixes

- Generate unique users, orgs, workspace names, ports, paths, and DB rows per test.
- Avoid shared mutable testcase structs in parallel subtests.
- Use temp dirs and cleanup checks that wait for background work to finish.
- Randomize test order in detection workflows to expose hidden coupling.
- Document helpers for unique names and isolated test resources.

## Suggested first slice

Add reusable unique-resource helpers and run randomized order checks on known-isolation packages.

<details>
<summary>References (20)</summary>

| ref | type | title | status | evidence |
| --- | --- | --- | --- | --- |
| [issue #2475](https://github.com/coder/coder/issues/2475) | issue | cli test flake TestServer/Telemetry | closed | ...etry ``` === Failed === FAIL: cli TestServer/Telemetry (0.01s) testing.go:1090: TempDir RemoveAll cleanup: unlinkat /var/folders/24/8k48jl6d249_n_qfxwsl6xvm0000gn/T/TestServerTelemetry4245994242/001: directory not empty --- FAIL: TestServer/Telemetry (0.01s) === FAIL: cli TestServer (0.03s) ``` more details at ht... |
| [issue #2709](https://github.com/coder/coder/issues/2709) | issue | Test flake: coderd TestUsersFilter | closed; linked_fix_merged | ...ror: POST http://127.0.0.1:52793/api/v2/users: unexpected status code 409: User already exists. Test: TestUsersFilter t.go:81: 2022-06-28 21:43:07.472 [DEBUG] (provisionerd) <github.com/coder/coder/provisionerd/provisionerd.go:370> (*Server).closeWithError closing server with error {"error": null} DONE 757 tests,... |
| [issue #10240](https://github.com/coder/coder/issues/10240) | issue | test flake: scaletest/createworkspaces Test_Runner/CleanupPendingBuild | closed | test flake: scaletest/createworkspaces Test_Runner/CleanupPendingBuild Seen here: https://github.com/coder/coder/actions/runs/6496433258/job/17643357736 Logs: https://gist.github.com/johnstcn/b43a9f8d34fbcfe5c7718a353f87ae73 test flake: scaletest/createworkspaces Test_Runner/CleanupPendingBuild Seen here: https://gi... |
| [issue #13910](https://github.com/coder/coder/issues/13910) | issue | flake: TestTracker_MultipleInstances | closed | ...coderd/workspacestats/tracker_test.go:156 Error: Received unexpected error: pq: duplicate key value violates unique constraint "templates_organization_id_name_idx" Test: TestTracker_M flake: TestTracker_MultipleInstances Seen here: https://github.com/coder/coder/runs/27527618569 ``` dbgen.go:97: Error Trace: /hom... |
| [issue #13962](https://github.com/coder/coder/issues/13962) | issue | flake: Test_sshConfigExecEscape | closed; linked_fix_merged | ...d - very intriguing. I don't see any way that can happen outside of tmpDir path collisions, but that would not be an easily reproducible flake. I can only assume the `WriteFile` function is returning before the `close` syscall can finish, somehow?? Given we're not testing any code here that's concurrent, it might... |
| [PR #1650](https://github.com/coder/coder/pull/1650) | PR | fix: Try to fix cli portforward test flakes | closed; merged | ...forward subcommand. - Guard against cmd running after test exit - Guard against port-reuse due to parallel tests fix: Try to fix cli portforward test flakes This PR attempts to fix test flakes in the portforward subcommand. - Guard against cmd running after test exit - Guard against port-reuse due to parallel tes... |
| [PR #2730](https://github.com/coder/coder/pull/2730) | PR | test: Try again in unit test if user already exists | closed; merged | test: Try again in unit test if user already exists test: Try again in unit test if user already exists test: Try again in unit test if user already exists coderd/coderdtest/coderdtest.go https://github.com/coder/coder/issues/2709 |
| [PR #2855](https://github.com/coder/coder/pull/2855) | PR | fix: Disable random workspace filter tests due to flakes | closed; merged | fix: Disable random workspace filter tests due to flakes Contributes towards #2854. fix: Disable random workspace filter tests due to flakes Contributes towards #2854. fix: Disable random workspace filter tests due to flakes Contributes towards #2854. coderd/workspaces_test.go This is actively causing failures on my... |
| [PR #6103](https://github.com/coder/coder/pull/6103) | PR | chore: fix flake in create-admin-user test | closed; merged | ...sts to use ed25519 instead of all available key types to avoid needing a lot of randomness from the system. chore: fix flake in create-admin-user test Switches all of the tests to use ed25519 instead of all available key types to avoid needing a lot of randomness from the system. chore: fix flake in create-admin-... |
| [PR #6116](https://github.com/coder/coder/pull/6116) | PR | fix: increase generated password length resolve flake | closed; merged | fix: increase generated password length resolve flake fix: increase generated password length resolve flake fix: increase generated password length resolve flake cli/usercreate.go |
| [PR #6494](https://github.com/coder/coder/pull/6494) | PR | chore: fix workspace audit log flake | closed; merged | ...bs/7618290591 coderd/workspaces_test.go This Pull Request is becoming stale. In order to minimize WIP, prevent merge conflicts and keep the tracker readable, I'm going close to this PR in 3 days if there isn't more activity. |
| [PR #8228](https://github.com/coder/coder/pull/8228) | PR | fix: fix TestPGCoordinatorDual_Mainline flake | closed; merged | .../runs/5376578815/jobs/9753922291?pr=8195 What was happening is that there was a duplicate update pushed, due to races in the test between connecting the clients, agents, and initial heartbeats. We attempt to suppress duplicates by serializing the updates to JSON, and comparing with the last update, but this is se... |
| [PR #9680](https://github.com/coder/coder/pull/9680) | PR | test: fix flaky TestPostWorkspacesByOrganization/TemplateNoTTL | closed; merged | ...ions/runs/6174322059/job/16759012795 Again, provisioning job in progress during cleanup. test: fix flaky TestPostWorkspacesByOrganization/TemplateNoTTL Spotted in: https://github.com/coder/coder/actions/runs/6174322059/job/16759012795 Again, provisioning job in progress during cleanup. test: fix flaky TestPostWor... |
| [PR #11501](https://github.com/coder/coder/pull/11501) | PR | fix: generate new random username to prevent flake | closed; merged | fix: generate new random username to prevent flake Closes https://github.com/coder/coder/issues/11497 fix: generate new random username to prevent flake Closes https://github.com/coder/coder/issues/11497 fix: generate new random username to prevent flake Closes https://github.com/coder/coder/issues/11497 cli/rename_... |
| [PR #21231](https://github.com/coder/coder/pull/21231) | PR | test(scaletest/workspacetraffic): fix test flake due to io.EOF on close | closed; merged | ...ive as there's an actual bug in `connectSSH` where closers are run in the wrong order. That _may_ be the cause, but there are some other branches as well that could potentially return `io.EOF`. Without a solid repro, though, this is speculative. |
| [PR #21660](https://github.com/coder/coder/pull/21660) | PR | test: fix flaky boundary test | closed; merged | test: fix flaky boundary test Closes https://github.com/coder/internal/issues/1297 Rewrite `TestBoundarySubcommand` in a way similar to `TestPrebuildsCommand`. test: fix flaky boundary test Closes https://github.com/coder/internal/issues/1297 Rewrite `TestBoundarySubcommand` in a way similar to `TestPrebuildsCommand... |
| [PR #25171](https://github.com/coder/coder/pull/25171) | PR | test(coderd): centralize chat test harness and stabilize flakes | closed; merged | ...ptions builder that installs the fake provider before the coderd test server so cleanup ordering is deterministic. Closes https://github.com/coder/internal/issues/1528 & Closes ENG-2659 Closes https://github.com/coder/internal/issues/1480 & Closes CODAGT-359 Closes https://github.com/coder/internal/issues/1507 &... |
| [PR #25630](https://github.com/coder/coder/pull/25630) | PR | chore: fix flake in TestResponsesInjectedTool | closed; merged | ...or reproduction. Due to AsyncRecorded token usages may be recorded in different order then expected. Fixes: https://github.com/coder/internal/issues/1544 chore: fix flake in TestResponsesInjectedTool Fixes flake in TestResponsesInjectedTool. See https://github.com/coder/coder/pull/25630/changes/d9bfeb20092129127a... |
| [PR #25667](https://github.com/coder/coder/pull/25667) | PR | ci: add Go test flake detector workflow | closed; merged | ...//github.com/coder/whichtests/commit/ec33bab1ec04cd86beb7a61a069db4463dba63f5). Reuses the `test-go-pg` composite (with its new `run-regex`, `test-shuffle`, and `gotestsum-json-file` inputs) and the `go-test-failure-report` composite, both introduced on the base branch (#25670), so this workflow shares one implem... |
| [PR #26132](https://github.com/coder/coder/pull/26132) | PR | test: fix transport error flake | closed; merged | ...njecting a failing `http.RoundTripper`, and add `testutil.RoundTripperFunc` for reuse. Generated by Coder Agents. <details> <summary>Implementation plan</summary> # Plan: Deterministic ResolveWorkspace transport error test ## Context `TestResolveWorkspace/TransportError` relied on closing an `httptest.Server` bef... |

</details>
