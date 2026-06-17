# Unknown or needs manual read

The downloaded metadata did not contain enough detail to classify the failure with confidence.

## Count

| references | issues | PRs |
| ---: | ---: | ---: |
| 25 | 1 | 24 |

## Why it flakes

Unknown is a signal that failure artifacts are too thin. It should shrink as intake and artifact capture improve.

## Common fixes

- Improve flake issue templates so reports include test name, package, job, platform, error signature, and rerun status.
- Upload logs, traces, screenshots, and last observed state for high-risk areas.
- Track unknowns separately instead of forcing fake precision.
- Manually read the highest-impact unknowns and reclassify them.

## Code examples

These examples are illustrative patterns for the category, not direct patches against one specific test.

<details>
<summary>Code examples</summary>

### Bad: file an unclassifiable flake report

```md
Test failed again. Rerun passed.
```

### Better: capture a minimum useful flake signature

```md
## Flake signature
- Test: TestWorkspaceAgentReconnect
- Package: coderd/workspaces
- Job: linux-amd64-postgres
- Platform: ubuntu-24.04, 4 CPU
- Error: timed out waiting for agent status connected
- Rerun: passed on attempt 2
- Artifacts: logs, trace, last observed agent state
```

### Bad: omit reproduction scope

```md
Saw a flake in CI. Not sure what happened.
```

### Better: include the targeted rerun command

```md
## Reproduction
- Command: `go test ./coderd -run TestWorkspaceAgentReconnect -count=50`
- Result: failed 2/50 on linux-amd64-postgres
- First failing seed/log: <artifact URL>
```

</details>

## Suggested first slice

Manually classify the top unknowns and use the gaps to improve the intake template.

<details>
<summary>References (25)</summary>

`solved by` is the author of the merged PR, either the reference itself or a linked fix PR. It is blank when the corpus did not identify a merged fix PR.

| ref | type | title | status | solved by | evidence |
| --- | --- | --- | --- | --- | --- |
| [issue #14151](https://github.com/coder/coder/issues/14151) | issue | flake: `TestUpdateUserProfile/UpdateSelfAsMember` | closed |  | flake: `TestUpdateUserProfile/UpdateSelfAsMember` https://github.com/coder/coder/actions/runs/10248312969/job/28349352329?pr=14117 ``` Error Trace: /home/runner/work/coder/coder/coderd/users_test.go:873 Error: Received unexpected error: PUT http://localhost:37491/api/v2/users/me/profile: unexpected status code 400:... |
| [PR #2343](https://github.com/coder/coder/pull/2343) | PR | fix: coderd: fix flaky test | closed; merged | [@johnstcn](https://github.com/johnstcn) | fix: coderd: fix flaky test This fixes a flaky test on slower platforms. This is not the ideal solution -- we'd probably want the deadline extension request to also include the time of creation, so that the backend can calculate accordingly. For now I'm just making the test less borderline. fix: coderd: fix flaky te... |
| [PR #7119](https://github.com/coder/coder/pull/7119) | PR | test: Handle Filter flake with ctx errors | closed; merged | [@Emyrk](https://github.com/Emyrk) | test: Handle Filter flake with ctx errors Fixes: https://github.com/coder/coder/issues/7114 test: Handle Filter flake with ctx errors Fixes: https://github.com/coder/coder/issues/7114 test: Handle Filter flake with ctx errors Fixes: https://github.com/coder/coder/issues/7114 coderd/rbac/authz.go coderd/rbac/authz_in... |
| [PR #7803](https://github.com/coder/coder/pull/7803) | PR | ci: add nightly flake workflow | closed; merged | [@ammario](https://github.com/ammario) | ci: add nightly flake workflow ci: add nightly flake workflow ci: add nightly flake workflow .github/workflows/nightly-flake.yaml |
| [PR #9666](https://github.com/coder/coder/pull/9666) | PR | test: fix flaky: TestDeleteTemplate/NoWorkspaces | closed; merged | [@mtojek](https://github.com/mtojek) | test: fix flaky: TestDeleteTemplate/NoWorkspaces It seems to be the same root cause as https://github.com/coder/coder/commit/e2579e944037bff083419c5313d98ec58389213a. test: fix flaky: TestDeleteTemplate/NoWorkspaces It seems to be the same root cause as https://github.com/coder/coder/commit/e2579e944037bff083419c531... |
| [PR #9865](https://github.com/coder/coder/pull/9865) | PR | fix: resolve flake in log sender by checking context | closed; merged | [@kylecarbs](https://github.com/kylecarbs) | fix: resolve flake in log sender by checking context See: https://github.com/coder/coder/actions/runs/6305051172/job/17117693579 fix: resolve flake in log sender by checking context See: https://github.com/coder/coder/actions/runs/6305051172/job/17117693579 fix: resolve flake in log sender by checking context See: h... |
| [PR #9931](https://github.com/coder/coder/pull/9931) | PR | test: fix flaky TestPostWorkspacesByOrganization/Create | closed; merged | [@mtojek](https://github.com/mtojek) | test: fix flaky TestPostWorkspacesByOrganization/Create Fixes: https://github.com/coder/coder/issues/9785 test: fix flaky TestPostWorkspacesByOrganization/Create Fixes: https://github.com/coder/coder/issues/9785 test: fix flaky TestPostWorkspacesByOrganization/Create Fixes: https://github.com/coder/coder/issues/9785... |
| [PR #10384](https://github.com/coder/coder/pull/10384) | PR | test(agent): fix service banner trim test flake | closed; merged | [@mafredri](https://github.com/mafredri) | test(agent): fix service banner trim test flake https://github.com/coder/coder/actions/runs/6613588583/job/17961742768?pr=10377 test(agent): fix service banner trim test flake https://github.com/coder/coder/actions/runs/6613588583/job/17961742768?pr=10377 test(agent): fix service banner trim test flake https://githu... |
| [PR #10875](https://github.com/coder/coder/pull/10875) | PR | chore: fix flake in templates_test.go | closed; merged | [@deansheather](https://github.com/deansheather) | chore: fix flake in templates_test.go It looks like multiple people have tried to fix similar flakes but no one checked to see if there were any more instances of the same problem in the same file... Fixes this flake https://github.com/coder/coder/actions/runs/7000137148/job/19040369936?pr=10590#step:5:464 chore: fi... |
| [PR #11521](https://github.com/coder/coder/pull/11521) | PR | chore(coderd): fix test flake in TestWorkspaceUpdateAutomaticUpdates_OK | closed; merged | [@johnstcn](https://github.com/johnstcn) | chore(coderd): fix test flake in TestWorkspaceUpdateAutomaticUpdates_OK Fixes a test flake seen here: https://github.com/coder/coder/actions/runs/7464047942/job/20310133108#step:5:471 Ordering of audit logs is not guaranteed. chore(coderd): fix test flake in TestWorkspaceUpdateAutomaticUpdates_OK Fixes a test flake... |
| [PR #12326](https://github.com/coder/coder/pull/12326) | PR | test(agent/agentscripts): fix test flake in `TestEnv` | closed; merged | [@mafredri](https://github.com/mafredri) | test(agent/agentscripts): fix test flake in `TestEnv` This should hopefully fix the following flake: https://github.com/coder/coder/actions/runs/8066720038/job/22035474376 It looks like the test output was correct, but we errored on asserting no error on `Execute`. Thus it looks like our test-routine exited too quic... |
| [PR #15724](https://github.com/coder/coder/pull/15724) | PR | chore(cli): fix test flake introduced by #15688 | closed; merged | [@johnstcn](https://github.com/johnstcn) | chore(cli): fix test flake introduced by #15688 chore(cli): fix test flake introduced by #15688 chore(cli): fix test flake introduced by #15688 cli/delete_test.go |
| [PR #17183](https://github.com/coder/coder/pull/17183) | PR | chore(mcp): fix test flakes | closed; merged | [@johnstcn](https://github.com/johnstcn) | chore(mcp): fix test flakes Closes https://github.com/coder/internal/issues/547 chore(mcp): fix test flakes Closes https://github.com/coder/internal/issues/547 chore(mcp): fix test flakes Closes https://github.com/coder/internal/issues/547 mcp/mcp_test.go |
| [PR #17559](https://github.com/coder/coder/pull/17559) | PR | chore: claude fixing flakes | closed; not_merged |  | chore: claude fixing flakes chore: claude fixing flakes chore: claude fixing flakes cli/templatepull_test.go |
| [PR #17604](https://github.com/coder/coder/pull/17604) | PR | chore(cli): fix test flake when running in coder workspace | closed; merged | [@johnstcn](https://github.com/johnstcn) | chore(cli): fix test flake when running in coder workspace This test was failing inside a Coder workspace due to `CODER_AGENT_TOKEN` being set. chore(cli): fix test flake when running in coder workspace This test was failing inside a Coder workspace due to `CODER_AGENT_TOKEN` being set. chore(cli): fix test flake wh... |
| [PR #17702](https://github.com/coder/coder/pull/17702) | PR | fix: resolve flake test on manager | closed; merged | [@defelmnq](https://github.com/defelmnq) | fix: resolve flake test on manager Fixes coder/internal#544 fix: resolve flake test on manager Fixes coder/internal#544 fix: resolve flake test on manager Fixes coder/internal#544 coderd/notifications/manager.go coderd/notifications/manager_test.go |
| [PR #17772](https://github.com/coder/coder/pull/17772) | PR | chore(cli): fix test flake in TestExpMcpServer | closed; merged | [@johnstcn](https://github.com/johnstcn) | chore(cli): fix test flake in TestExpMcpServer Test was failing inside a Coder workspace. chore(cli): fix test flake in TestExpMcpServer Test was failing inside a Coder workspace. chore(cli): fix test flake in TestExpMcpServer Test was failing inside a Coder workspace. cli/exp_mcp_test.go |
| [PR #18311](https://github.com/coder/coder/pull/18311) | PR | test: fix test flake in TestDynamicParametersWithTerraformValues | closed; merged | [@Emyrk](https://github.com/Emyrk) | test: fix test flake in TestDynamicParametersWithTerraformValues Wrong build ID was being used for the await. Closes https://github.com/coder/internal/issues/687 test: fix test flake in TestDynamicParametersWithTerraformValues Wrong build ID was being used for the await. Closes https://github.com/coder/internal/issu... |
| [PR #19026](https://github.com/coder/coder/pull/19026) | PR | chore: fix TestManagedAgentLimit flake | closed; merged | [@deansheather](https://github.com/deansheather) | chore: fix TestManagedAgentLimit flake Closes https://github.com/coder/internal/issues/812 chore: fix TestManagedAgentLimit flake Closes https://github.com/coder/internal/issues/812 chore: fix TestManagedAgentLimit flake Closes https://github.com/coder/internal/issues/812 enterprise/coderd/coderd.go enterprise/coder... |
| [PR #20368](https://github.com/coder/coder/pull/20368) | PR | fix: replace blink with ci-flake-bot agent | closed; merged | [@ibetitsmike](https://github.com/ibetitsmike) | fix: replace blink with ci-flake-bot agent Fixes: https://github.com/coder/security/issues/109 fix: replace blink with ci-flake-bot agent Fixes: https://github.com/coder/security/issues/109 fix: replace blink with ci-flake-bot agent Fixes: https://github.com/coder/security/issues/109 .github/workflows/ci.yaml .githu... |
| [PR #20379](https://github.com/coder/coder/pull/20379) | PR | fix: replace ci-flake-bot app-id with slack's user id | closed; merged | [@ibetitsmike](https://github.com/ibetitsmike) | fix: replace ci-flake-bot app-id with slack's user id <!-- If you have used AI to produce some or all of this PR, please ensure you have read our [AI Contribution guidelines](https://coder.com/docs/about/contributing/AI_CONTRIBUTING) before submitting. --> fix: replace ci-flake-bot app-id with slack's user id <!-- I... |
| [PR #21658](https://github.com/coder/coder/pull/21658) | PR | ci: skip flaky test | closed; merged | [@evgeniy-scherbina](https://github.com/evgeniy-scherbina) | ci: skip flaky test ci: skip flaky test ci: skip flaky test enterprise/cli/boundary_test.go |
| [PR #24112](https://github.com/coder/coder/pull/24112) | PR | fix: resolve Test_batcherFlush/RetriesOnTransientFailure flake | closed; merged | [@sreya](https://github.com/sreya) | fix: resolve Test_batcherFlush/RetriesOnTransientFailure flake fixes https://github.com/coder/internal/issues/1452 fix: resolve Test_batcherFlush/RetriesOnTransientFailure flake fixes https://github.com/coder/internal/issues/1452 fix: resolve Test_batcherFlush/RetriesOnTransientFailure flake fixes https://github.com... |
| [PR #25177](https://github.com/coder/coder/pull/25177) | PR | test(coderd/x/chatd): skip stale notification flakes | closed; merged | [@ibetitsmike](https://github.com/ibetitsmike) | test(coderd/x/chatd): skip stale notification flakes Skip the chatd tests that currently flake because the control notification flow cannot distinguish stale wake/status NOTIFY payloads from real interrupt requests. Each skipped test includes a TODO to re-enable it after the chatd notification flow refactor handles... |
| [PR #25934](https://github.com/coder/coder/pull/25934) | PR | ci: install gotestsum in flake check workflow | closed; merged | [@ThomasK33](https://github.com/ThomasK33) | ci: install gotestsum in flake check workflow The Flake Check workflow runs `make test` through the `test-go-pg` action, which invokes `gotestsum`, but the workflow never installs it. The mise refactor (#25727) deleted the `setup-go` action that previously installed `gotestsum` implicitly, and added explicit `mise i... |

</details>
