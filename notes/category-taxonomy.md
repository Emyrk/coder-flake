# Coder flake failure-mode taxonomy

Generated from `processed/candidate_issues.csv`, `processed/candidate_prs.csv`, and the raw GitHub JSON under `raw/`.

Corpus categorized: 563 rows, 219 issues and 344 PRs.

The categorization is heuristic. The `evidence` column in `processed/categories.csv` is the audit trail for each row.

## Category counts

| category | total | issues | PRs |
| --- | ---: | ---: | ---: |
| networking/proxy/websocket | 105 | 65 | 40 |
| workspace/agent lifecycle | 102 | 44 | 58 |
| concurrency/race | 74 | 35 | 39 |
| browser/e2e/playwright | 47 | 15 | 32 |
| database/transactions/migrations | 47 | 15 | 32 |
| timing/eventual consistency | 46 | 15 | 31 |
| not-a-test-flake/nix-flake-or-maintenance | 41 | 3 | 38 |
| platform/os-specific CI behavior | 31 | 5 | 26 |
| unknown/needs manual read | 25 | 1 | 24 |
| resource exhaustion/timeout | 21 | 14 | 7 |
| test isolation/order dependency | 20 | 5 | 15 |
| external service/dependency | 4 | 2 | 2 |

## Taxonomy

### networking/proxy/websocket

Transport-layer flakes: SSH, websockets, tunnels, tailnet/DERP/WireGuard/WebRTC, sockets, ports, TLS, x509, and proxy behavior.

Representative examples:
- issue #1644: flake: peer TestConn/Buffering (closed; linked_fix_merged, linked fixes #1774;#3086). Evidence: …"arm64" GOHOSTOS="darwin" GOINSECURE="" GOMODCACHE="/Users/cian/go/pkg/mod" GONOPROXY="" GONOSUMDB="" GOOS="darwin" GOPATH="/Users/cian/go" GOPRIVATE="" GOPROXY="https://proxy.golang.org,direct" GOROOT="/opt/homebrew/Cellar/go/1.18.2/libexec" GOSUMDB="sum.golang.org" GOTMPDIR="" GOTOOLDIR="/opt/homebrew/Cell flake: peer TestConn/Buffering ``` GO111MODULE="" GOARCH="arm64" GOBIN="" GOCACHE="/Users/cian/Library/Caches/…
- issue #9107: test flake: TestDERPHeaders (closed; linked_fix_merged, linked fixes #9262). Evidence: test flake: TestDERPHeaders `coder ping` can apparently sometimes succeed without calling DERP from the client side. sometimes we get ``` ptytest.go:131: 2023-08-15 09:59:53.190: cmd: "pong from upbeat-aryabhata8-p2T p2p via 172.20.0.6:60589 in 0s" ``` instead of ``` ptytest.go:131: 2023-08-15 10:13:31.289: cmd: "pong from kind-hopper4-9WU proxied via DERP(Coder Embedded Relay) in 1ms" ``` and `/derp` is never called…
- issue #10832: flake: TestWorkspaceAgentListeningPorts/LinuxAndWindows/OK (closed; linked_fix_merged, linked fixes #10833). Evidence: …gPorts/LinuxAndWindows/OK ``` workspaceagents_test.go:679: expected to not find TCP port 35549 in response ``` seen on: https://github.com/coder/coder/actions/runs/6943682346/job/18902742899 flake: TestWorkspaceAgentListeningPorts/LinuxAndWindows/OK ``` workspaceagents_test.go:679: expected to not find TCP port 35549 in response ``` seen on: https://github.com/coder/coder/actions/runs/6943682346/job/18902742899 PR #1…
- issue #12277: flake: TestDERPEndToEnd nil pointer in DERPMap (closed; linked_fix_merged, linked fixes #12280). Evidence: flake: TestDERPEndToEnd nil pointer in DERPMap Seen here: https://github.com/coder/coder/actions/runs/8004918533/job/21863235595 Somehow, in TestDERPEndToEnd the DERP map ends up with a null region ``` t.go:99: 2024-02-22 13:05:06.248 [info] inmem-provisionerd-test: provisioner daemon disconnected ... error= InmemoryListener is already closed: use of closed network connection storj.io/drpc/drpcserver.(*Server).Serve:…

### workspace/agent lifecycle

Coder workspace, provisioner, agent, PTY, reconnect, template-version, workspace build/log, desktop, container, or agent API lifecycle flakes.

Representative examples:
- issue #382: Fix provisionerd test flake panic (closed; linked_fix_merged, linked fixes #383). Evidence: Fix provisionerd test flake panic https://github.com/coder/coder/runs/5364357063?check_suite_focus=true#step:7:198 Fix provisionerd test flake panic https://github.com/coder/coder/runs/5364357063?check_suite_focus=true#step:7:198 PR #383: test: Fix test flake panic in provisionerd Closes #382.
- issue #1368: Bug: test flake - Test/go/PostgreSQL TestWorkspaceAgentPTY  (closed; linked_fix_merged, linked fixes #1562). Evidence: Bug: test flake - Test/go/PostgreSQL TestWorkspaceAgentPTY ## Expected TestWorkspaceAgentPTY should consistently succeed or fail ## Actual after failure, rerunning the test causes it to succeed ## Logs https://github.com/coder/coder/actions/runs/2302105303/attempts/1 Bug: test flake - Test/go/PostgreSQL TestWorkspaceAgentPTY ## Expected TestWorkspaceAgentPTY should consistently succeed or fail ## Actual after failure…
- issue #2603: streaming job logs race condition means not all logs are returned / TestDelete flake (closed; linked_fix_merged, linked fixes #2732;#2783;#5353). Evidence: streaming job logs race condition means not all logs are returned / TestDelete flake Relates to #2347 HTTP endpoint `/api/v2/workspacebuilds/<build>/logs` will sometimes end without returning all logs. This causes our `TestDelete` cli tests to be flaky because they wait for the final "Cleaning Up" log which sometimes never comes, e.g. ``` ptytest.go:92: match exceeded deadline: wanted "Cleaning Up"; got "\x1b[1A\r✔ Q…
- issue #5159: Fix flake test TestProvisionerd/ReconnectAndComplete (closed; linked_fix_unmerged_or_unknown, linked fixes #5160). Evidence: Fix flake test TestProvisionerd/ReconnectAndComplete This test has been failing quite frequently https://github.com/coder/coder/actions/runs/3532958155/jobs/5928185794 Fix flake test TestProvisionerd/ReconnectAndComplete This test has been failing quite frequently https://github.com/coder/coder/actions/runs/3532958155/jobs/5928185794 Hopefully fixed (or at least alleviated by #5169), let's re-open if it is still a pr…

### concurrency/race

Shared-memory, goroutine, locking, cancellation, pubsub, or data-race failures where interleavings change the result.

Representative examples:
- issue #3747: test flake: data race in TestFeaturesService_EntitlementsAPI (closed; linked_fix_merged, linked fixes #3765). Evidence: test flake: data race in TestFeaturesService_EntitlementsAPI ``` === Failed === FAIL: enterprise/coderd TestFeaturesService_EntitlementsAPI/NoLicense (0.00s) testing.go:1319: race detected during execution of test --- FAIL: TestFeaturesService_EntitlementsAPI/NoLicense (0.00s) === FAIL: enterprise/coderd TestFeaturesService_EntitlementsAPI/FullLicense (0.00s) testing.go:1319: race detected during execution of test --…
- issue #4607: flake: TestReplica/TwentyConcurrent (closed; linked_fix_merged, linked fixes #4842). Evidence: flake: TestReplica/TwentyConcurrent ``` === FAIL: enterprise/replicasync TestReplica/TwentyConcurrent (1.65s) testing.go:1319: race detected during execution of test --- FAIL: TestReplica/TwentyConcurrent (1.65s) ``` See [run](https://github.com/coder/coder/actions/runs/3269194749/jobs/5376440207) flake: TestReplica/TwentyConcurrent ``` === FAIL: enterprise/replicasync TestReplica/TwentyConcurrent (1.65s) testing.go:…
- issue #9340: test flake: Fail in goroutine after TestProvisionerd/InstantClose has completed (closed; linked_fix_merged, linked fixes #9709). Evidence: test flake: Fail in goroutine after TestProvisionerd/InstantClose has completed ``` # on main@3b1ecd3c2 $ go test -race -count=100 ./provisionerd/ panic: Fail in goroutine after TestProvisionerd/InstantClose has completed goroutine 1605 [running]: testing.(*common).Fail(0xc00064f6c0) /nix/store/l9n531fcx4grk3wvfbigya3p66scj61h-go-1.20.6/share/go/src/testing/testing.go:933 +0x1a8 testing.(*common).Error(0xc00064f6c0, …
- issue #14143: flake: `TestSSH/RemoteForward` (closed; linked_fix_merged, linked fixes #14195). Evidence: …ou. If this was in error, please reassign it. ```go ================== WARNING: DATA RACE Write at 0x00c075c4ad98 by goroutine 42789: runtime.racewrite() <autogenerated>:1 +0x1e github.com/coder/coder/v2/tailnet.(*Conn).Close() /home/runner/work/coder/coder/tail flake: `TestSSH/RemoteForward` https://github.com/coder/coder/actions/runs/10246342180/job/28343288836?pr=14117 @ethanndickson looks like you touched the cod…

### browser/e2e/playwright

Browser-driven or frontend integration tests, including Playwright, Storybook, page/locator waits, and JS UI harness failures.

Representative examples:
- issue #10481: flake: SSHKeyPage.test.tsx has too many element matches (closed; linked_fix_merged, linked fixes #10553). Evidence: flake: SSHKeyPage.test.tsx has too many element matches Had this happen earlier today, but for some reason, I can't find the logs in the actions that ran. Not sure if re-running the test caused the logs to get wiped. Either way, there's an issue that sometimes triggers on `SSHKeyPage.test.tsx`. [Here's a failing run](https://github.com/coder/coder/actions/runs/6589196703/job/17903112550) Here's what looks like the mo…
- issue #13240: Test flake: Tests for `useClipboard` don't consistently flush state changes (closed; linked_fix_merged, linked fixes #13250). Evidence: …al, so depending on what's found after digging, it might be better to make some E2E tests instead - Though obviously it'd be better to have a single test for the clipboard, rather than needing to have ad-hoc tests for everything that just happens to use the clipboard - The main issue is that React Testing Library will inject a clipboard mock the moment you try to set up any kind of user session with `user.setup`. Thi…
- issue #5309: flaky: WorkspacePage exceeded timeout of 5000 ms for a test (closed). Evidence: flaky: WorkspacePage exceeded timeout of 5000 ms for a test Spotted in: https://github.com/coder/coder/actions/runs/3629622036/jobs/6122043573 ``` Summary of all failing tests FAIL src/pages/WorkspacePage/WorkspacePage.test.tsx (33.78 s) ● WorkspacePage › requests a delete job when the user presses Delete and confirms thrown: "Exceeded timeout of 5000 ms for a test. Use jest.setTimeout(newTimeout) to increase the tim…
- issue #9424: test flake: test-e2e tests/createWorkspace.spec.ts:105:5 › create workspace and overwrite default parameters  (closed). Evidence: test flake: test-e2e tests/createWorkspace.spec.ts:105:5 › create workspace and overwrite default parameters seen in https://github.com/coder/coder/actions/runs/6015567350/job/16317708669#step:10:2912 <details> <summary>Details</summary> ```console 1) [tests] › tests/createWorkspace.spec.ts:105:5 › create workspace and overwrite default parameters Test timeout of 60000ms exceeded. Error: page.waitForSelector: Target …

### database/transactions/migrations

Postgres, SQL, migrations, database cleanup, transaction semantics, or DB-backed tests.

Representative examples:
- issue #388: Investigate test flake for allocating ports with PostgreSQL Docker (closed; linked_fix_merged, linked fixes #389). Evidence: Investigate test flake for allocating ports with PostgreSQL Docker https://github.com/coder/coder/runs/5375197003?check_suite_focus=true#step:9:52 Investigate test flake for allocating ports with PostgreSQL Docker https://github.com/coder/coder/runs/5375197003?check_suite_focus=true#step:9:52 PR #389: test: Add mutex to opening PostgreSQL ports to prevent collision Closes #388.
- issue #2347: CI test/go/postgres is flaky (closed; linked_fix_merged, linked fixes #2413). Evidence: CI test/go/postgres is flaky these tests are timing out en-mass on many runs, e.g. https://github.com/coder/coder/actions/runs/2502674150/attempts/2 Need to investigate, but some possible issues: * we set parallel=1 and timeout=5m --- are these tests just taking too long? * are any postgres workers getting OOM killed? * are there deadlocks in parallel tests? * does it matter that we don't clean up test databases when…
- issue #6197: chore: test flake: TestTemplateVersionDryRun/OK (closed). Evidence: …``` Unable to reproduce locally. Ran test 100 times with race detector on with `DB=ci`. chore: test flake: TestTemplateVersionDryRun/OK Seen here: https://github.com/coder/coder/actions/runs/4172299609/jobs/7223229286 ``` templateversions_test.go:713: Error Trace: /home/runner/work/coder/coder/coderd/templateversions_test.go:713 /home/runner/work/coder/coder/coderd/asm_amd64.s:1598 Error: "0" is not greater than or e…
- issue #10219: test flake: TestServerDBCrypt (closed). Evidence: test flake: TestServerDBCrypt **Test execution link**: [TestServerDBCrypt](https://app.datadoghq.com/ci/test/AgAAAYsCC68gAnzXGQAAAAAAAAAYAAAAAEFZc0NDNjhnQUFDUFVBcjRkY1ZRcEZaOQAAACQAAAAAMDE4YjAyMGMtOWYyYS00ZjQ3LWFhN2ItMmU2MzM3ZGJmNjli) **Service**: coder **Branch**: [main](https://app.datadoghq.com/ci/test-branch/github.com%2Fcoder%2Fcoder/coder/main?env=none) **Commit**: [127f65c98b7f7d900798de66cb2d1bccc3e7ea63](htt…

### timing/eventual consistency

Async systems observed too early or with brittle temporal assertions: polling, retry, sleep, TTL, metrics/insights aggregation, log visibility, and deterministic-time fixes.

Representative examples:
- issue #12509: flake: insights (closed; linked_fix_merged, linked fixes #12517). Evidence: flake: insights From https://github.com/coder/coder/actions/runs/8229639076/job/22501248571?pr=12468 ```bash insights_test.go:108: Error Trace: /home/runner/actions-runner/_work/coder/coder/coderd/insights_test.go:108 Error: Not equal: expected: &codersdk.DAUsResponse{Entries:[]codersdk.DAUEntry{codersdk.DAUEntry{Date:"2024-03-11", Amount:1}}, TZHourOffset:6} actual : &codersdk.DAUsResponse{Entries:[]codersdk.DAUEntr…
- issue #3420: `TestServer/Prometheus` test flake (closed). Evidence: `TestServer/Prometheus` test flake c.f. https://github.com/coder/coder/actions/runs/2821006778/attempts/1 ``` === Failed === FAIL: cli TestServer/Prometheus (0.19s) server_test.go:428: Error Trace: /home/runner/work/coder/coder/cli/server_test.go:428 Error: Should be true Test: TestServer/Prometheus --- FAIL: TestServer/Prometheus (0.19s) === FAIL: cli TestServer (0.20s) ``` `TestServer/Prometheus` test flake c.f. ht…
- issue #5323: flaky: coderd/prometheusmetrics TestWorkspaces/Multiple (closed). Evidence: flaky: coderd/prometheusmetrics TestWorkspaces/Multiple Spotted in: https://github.com/coder/coder/actions/runs/3630546787/jobs/6124020920 ``` === FAIL: coderd/prometheusmetrics TestWorkspaces/Multiple (5.00s) prometheusmetrics_test.go:227: Error Trace: /home/runner/work/coder/coder/coderd/prometheusmetrics/prometheusmetrics_test.go:227 /home/runner/work/coder/coder/coderd/prometheusmetrics/asm_amd64.s:1594 Error: No…
- issue #6481: flake: coderd_test.TestTemplateMetrics (closed). Evidence: flake: coderd_test.TestTemplateMetrics `TestTemplateMetrics` in `coderd/templates_test.go` is disabled because it flakes often in my experience when running the full test suite. flake: coderd_test.TestTemplateMetrics `TestTemplateMetrics` in `coderd/templates_test.go` is disabled because it flakes often in my experience when running the full test suite. ``` templates_test.go:804: Error Trace: /home/coder/coder/coderd…

### not-a-test-flake/nix-flake-or-maintenance

Search false positives or maintenance PRs about Nix flakes, flake.lock, or update-flake automation rather than nondeterministic tests.

Representative examples:
- issue #7834: add coder package derivation to nix flake (closed). Evidence: add coder package derivation to nix flake It would be awesome to be able to install coder directly from this flake to get the latest version. In nixpkgs the coder version seems to still be at 0.17.1: https://search.nixos.org/packages?channel=unstable&from=0&size=50&sort=relevance&type=packages&query=coder Currently have to manually overwrite the version and src using `pkgs.coder.overrideAttrs` which isn't a huge issu…
- issue #14343: Ensure all dependencies defined in `flake.nix` and our GitHub Actions are aligned (closed). Evidence: Ensure all dependencies defined in `flake.nix` and our GitHub Actions are aligned For example, I'm having a hell of a time trying to generate some protobuf definitions which pass CI because `protoc-gen-go` is not locked in our nix flake, while it's using a fixed version in `.github/workflows/ci.yaml`. ```yaml - name: go install tools run: \| go install google.golang.org/protobuf/cmd/protoc-gen-go@v1.30 ``` ```bash [ni…
- issue #26127: nix: flake.nix build fails - google-chrome-stable_138.0.7204.49 returns 404 from Google CDN (open). Evidence: nix: flake.nix build fails - google-chrome-stable_138.0.7204.49 returns 404 from Google CDN ## Bug `nix develop` and `nix-shell shell.nix` fail on Linux because `google-chrome-stable_138.0.7204.49` has been deleted from Google's CDN. ## Environment - OS: Fedora - Nix flake nixpkgs pin: rev `50ab793` (flake.lock) - Relevant line: `flake.nix:192` ## Error ```text error: Cannot build '/nix/store/af59wjk8a8ys18bam92y3jns…
- PR #6173: fix: Update flake.lock to fix Go build (closed; merged). Evidence: fix: Update flake.lock to fix Go build Related: https://github.com/coder/coder/pull/5968 This PR fixes build problems with Go 1.20. I can see this error when I enter the `coder` directory. ``` … while calling anonymous lambda at /nix/store/vgx3678yb41cb8g2g66nlj1alf3ksh92-source/pkgs/stdenv/generic/make-derivation.nix:192:81: 191\| checkDependencyList = checkDependencyList' []; 192\| checkDependencyList' = positions: n…

### platform/os-specific CI behavior

Behavior that only reproduces on a particular CI OS or architecture, especially Windows, macOS, Darwin, zsh, ARM64, or host shell differences.

Representative examples:
- issue #14877: flake: `TestAPIKey_Refresh` (closed; linked_fix_merged, linked fixes #14888). Evidence: …cally, nor could I get the test to run that quickly. (It also might have been a Windows time precision issue? I on
- issue #998: Bug: Flake tests for coder / test/go (windows-2022) job (closed). Evidence: Bug: Flake tests for coder / test/go (windows-2022) job Failing job: https://github.com/coder/coder/runs/6012008795?check_suite_focus=true Bug: Flake tests for coder / test/go (windows-2022) job Failing job: https://github.com/coder/coder/runs/6012008795?check_suite_focus=true This is not happening anymore so I'm closing this.
- issue #10202: test flake: scaletest/createworkspaces Test_Runner/OK (closed). Evidence: …etest/createworkspaces/run_test.go:552 /Users/runner/hostedtoolcache/go/1.20.10/arm64/src/runtime/asm_arm64.s:1172 Error: Condition never satisfied Test: Test_Runner/OK ``` seen on https://github.com/coder/coder/runs/17574663493 test flake: scaletest/createworkspaces Test_Runner/OK ``` run_test.go:552: Error Trace: /Users/runner/work/coder/coder/coderd/coderdtest/coderdtest.go:862 /Users/runner/work/coder/coder/scale…
- issue #11239: flake: TestTunnel (unknown) (closed). Evidence: flake: TestTunnel (unknown) Seen here (windows-2022): https://github.com/coder/coder/actions/runs/7225357149/job/19688636024 ``` === Failed === FAIL: coderd/devtunnel TestTunnel (unknown) === FAIL: coderd/devtunnel TestTunnel/V1 (unknown) === FAIL: coderd/devtunnel TestTunnel/V2 (unknown) ``` No further information available. flake: TestTunnel (unknown) Seen here (windows-2022): https://github.com/coder/coder/actions…

### unknown/needs manual read

Not enough signal in the downloaded metadata to assign a reliable failure mode without reading the linked run, code, or full discussion.

Representative examples:
- issue #14151: flake: `TestUpdateUserProfile/UpdateSelfAsMember` (closed). Evidence: flake: `TestUpdateUserProfile/UpdateSelfAsMember` https://github.com/coder/coder/actions/runs/10248312969/job/28349352329?pr=14117 ``` Error Trace: /home/runner/work/coder/coder/coderd/users_test.go:873 Error: Received unexpected error: PUT http://localhost:37491/api/v2/users/me/profile: unexpected status code 400: Validation failed. username: Validation failed for tag "username" with value: "condescending-chandrasek…
- PR #2343: fix: coderd: fix flaky test (closed; merged, linked fixes #2343). Evidence: fix: coderd: fix flaky test This fixes a flaky test on slower platforms. This is not the ideal solution -- we'd probably want the deadline extension request to also include the time of creation, so that the backend can calculate accordingly. For now I'm just making the test less borderline. fix: coderd: fix flaky test This fixes a flaky test on slower platforms. This is not the ideal solution -- we'd probably want th…
- PR #7119: test: Handle Filter flake with ctx errors (closed; merged, linked fixes #7119). Evidence: test: Handle Filter flake with ctx errors Fixes: https://github.com/coder/coder/issues/7114 test: Handle Filter flake with ctx errors Fixes: https://github.com/coder/coder/issues/7114 test: Handle Filter flake with ctx errors Fixes: https://github.com/coder/coder/issues/7114 coderd/rbac/authz.go coderd/rbac/authz_internal_test.go coderd/rbac/error.go > This _looks_ right to me, I think this is a tricky flake to hit. …
- PR #7803: ci: add nightly flake workflow (closed; merged, linked fixes #7803). Evidence: ci: add nightly flake workflow ci: add nightly flake workflow ci: add nightly flake workflow .github/workflows/nightly-flake.yaml

### resource exhaustion/timeout

Slow or overloaded runs, deadline/context timeouts, buffer exhaustion, OOM, CPU/memory pressure, and explicit test timeout adjustments.

Representative examples:
- issue #2335: test flake: coderd/devtunnel TestTunnel (closed; linked_fix_merged, linked fixes #3050). Evidence: …890362136?check_suite_focus=true#step:10:76)-144da60e49d9.wg-tunnel.coder.app": context deadline exceeded (Client.T test flake: coderd/devtunnel TestTunnel c.f. https://github.com/coder/coder/actions/runs/2498710623/attempts/1 ``` === FAIL: coderd/devtunnel TestTunnel (159.50s) tunnel_test.go:47: https://fcca5909-53f1-4de6-a275-144da60e49d9.wg-tunnel.coder.app/ tunnel_test.go:61: Error Trace: tunnel_test.go:61 asm_am…
- issue #5187: Flaky: loadtest/reconnectingpty (closed). Evidence: Flaky: loadtest/reconnectingpty I'm not able to pass CI tests and simply burning CPU cycles on this test: ``` "error": connection closed storj.io/drpc/drpcstream.(*Stream).sendPacket:268 storj.io/drpc/drpcstream.(*Stream).CloseSend:501 storj.io/drpc/drpcserver.(*Server).handleRPC:126 storj.io/drpc/drpcserver.(*Server).ServeOne:66 storj.io/drpc/drpcserver.(*Server).Serve.func2:112 storj.io/drpc/drpcctx.(*Tracker).trac…
- issue #5343: flaky: TestWorkspaceAppsNonCanonicalHeaders  (closed). Evidence: …et "http://localhost:50992/@me/adoring-dirac1/apps/test-app-owner/?query=true": context deadline exceeded Test: TestWorkspaceAppsNonCanonicalHeaders/ProxyPath t.go:81: 2022-12-08 05:34:58.441 [WARN] <github.com/coder/coder/coderd/httpmw/logger.go:63> Logger.func1.1.1 GET flaky: TestWorkspaceAppsNonCanonicalHeaders Spotted in: https://github.com/coder/coder/actions/runs/3645591250/jobs/6155866531 ``` workspaceapps_tes…
- issue #8968: test flake: coderd TestWorkspaceWatcher (closed). Evidence: …e/runner/actions-runner/_work/coder/coder/coderd/workspaces_test.go:2200 Error: timed out waiting for event Test: TestWorkspaceWatcher Messages: workspace build faile test flake: coderd TestWorkspaceWatcher c.f. https://github.com/coder/coder/actions/runs/5797085582/job/15711945289?pr=8939 ``` t.go:85: 2023-08-08 12:47:44.211 [info] TestWorkspaceWatcher: done waiting for event event="workspace build pending or failed…

### test isolation/order dependency

State leaking across tests: temp dirs, cache, duplicate names, timestamp collisions, random ordering, reused ports, cleanup gaps, or parallel-test interference.

Representative examples:
- issue #2709: Test flake: coderd TestUsersFilter (closed; linked_fix_merged, linked fixes #2730). Evidence: …ror: POST http://127.0.0.1:52793/api/v2/users: unexpected status code 409: User already exists. Test: TestUsersFilter t.go:81: 2022-06-28 21:43:07.472 [DEBUG] (provisionerd) <github.com/coder/coder/provisionerd/provisionerd.go:370> (*Server).closeWithError closing server with error {"error": null} DONE 757 tests, 2 skipped, 1 failure in 72.970s ``` I suspect this has to do with the fact that we create 15 users with r…
- issue #13962: flake: Test_sshConfigExecEscape (closed; linked_fix_merged, linked fixes #14233). Evidence: …d - very intriguing. I don't see any way that can happen outside of tmpDir path collisions, but that would not be an easily reproducible flake. I can only assume the `WriteFile` function is returning before the `close` syscall can finish, somehow?? Given we're not testing any code here that's concurrent, it might be worth just removing the parallel call to stop the flake? Nice find @ethanndickson! The path collision …
- issue #2475: cli test flake TestServer/Telemetry (closed). Evidence: …etry ``` === Failed === FAIL: cli TestServer/Telemetry (0.01s) testing.go:1090: TempDir RemoveAll cleanup: unlinkat /var/folders/24/8k48jl6d249_n_qfxwsl6xvm0000gn/T/TestServerTelemetry4245994242/001: directory not empty --- FAIL: TestServer/Telemetry (0.01s) === FAIL: cli TestServer (0.03s) ``` more details at https://github.com/coder/coder/actions/runs/2517125335/attempts/1 cli test flake TestServer/Telemetry ``` ==…
- issue #10240: test flake: scaletest/createworkspaces Test_Runner/CleanupPendingBuild (closed). Evidence: test flake: scaletest/createworkspaces Test_Runner/CleanupPendingBuild Seen here: https://github.com/coder/coder/actions/runs/6496433258/job/17643357736 Logs: https://gist.github.com/johnstcn/b43a9f8d34fbcfe5c7718a353f87ae73 test flake: scaletest/createworkspaces Test_Runner/CleanupPendingBuild Seen here: https://github.com/coder/coder/actions/runs/6496433258/job/17643357736 Logs: https://gist.github.com/johnstcn/b43…

### external service/dependency

Failures rooted in outside services or dependency managers such as Yarn, Datadog, Docker setup, AWS, registries, or CDN availability.

Representative examples:
- issue #10105:  flake: WorkspaceSchedulePage › autostop › uses template default ttl when first enabled (closed). Evidence: …\| FormLanguage.stopSwitch, 273 \| ); 274 \| // enable autostop at waitForWrapper (node_modules/.pnpm/@testing-library+dom@9.3.1/node_modules/@testing-library/dom/dist/wait-for.js:160:27) at node_modules/.pnpm/@testing-library+dom@9.3.1/node_modules/@testing-library/dom/dist/query-helpers.js:86:31 at Object.findByLabelText (src/pages/WorkspaceSettingsPage/WorkspaceSchedulePage/WorkspaceSchedulePage.test.tsx:[271](https:…
- issue #14535: flake: `UsersPage.test.tsx` (closed). Evidence: …moreButtons[0]; 28 \| await user.click(firstMoreButton); 29 \| at waitForWrapper (node_modules/.pnpm/@testi flake: `UsersPage.test.tsx` https://github.com/coder/coder/actions/runs/10680634527/job/29602816185 ``` FAIL src/pages/UsersPage/UsersPage.test.tsx (19.402 s) ● UsersPage › suspend user › when it is success › shows a success message ... 24 \| const user = userEvent.setup(); 25 \| // Get the first user in the table …
- PR #23877: test(coderd/x/chatd): remove flaky OpenAI round-trip tests (closed; merged, linked fixes #23877). Evidence: …rom `coderd/x/chatd/integration_test.go` and drop the now-unused fake upstream capture code. Closes https://github.com/coder/internal/issues/1433 test(coderd/x/chatd): remove flaky OpenAI round-trip tests These OpenAI reasoning + web search round-trip integration tests keep flaking in CI even after the recent timing fix. Remove both variants from `coderd/x/chatd/integration_test.go` and drop the now-unused fake upstr…
- PR #25015: fix(coderd/externalauth): isolate TestValidateToken transports to fix flake (closed; merged, linked fixes #25015). Evidence: fix(coderd/externalauth): isolate TestValidateToken transports to fix flake This change uses separate http clients/transports in TestValidateToken subtests. Previously parallel subtests of TestValidateToken shared http.DefaultTransport. When one subtest's httptest.Server.Close() ran in t.Cleanup, it called http.DefaultTransport.CloseIdleConnections, which could interrupt connection(s) used in another subtest. https:/…

## Notes on interpretation

- Rows are categorized independently. A linked issue and fix PR can land in different categories if the PR title/body exposes a more specific cause than the issue report.
- `not-a-test-flake/nix-flake-or-maintenance` is intentional. The seed search matched `flake.nix` and update-flake maintenance work, which is not nondeterministic test flakiness.
- `unknown/needs manual read` means the local metadata did not contain enough cause text. It does not mean the failure is unknowable.
- Categories are failure-mode oriented, not component ownership. For example, a workspace agent websocket failure should be networking if the transport is the root signal, and workspace/agent lifecycle if the lifecycle sequencing is the root signal.
