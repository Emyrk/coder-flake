# Common solutions for Coder flakes

Source data: `processed/categories.csv`, `notes/category-taxonomy.md`, and raw GitHub issue/PR JSON under `raw/`.

Corpus: 563 categorized rows, 219 issues and 344 PRs. Counts below are category counts from the taxonomy, not unique root causes. Linked examples cite the issue or PR number present in the corpus.

## Cross-category themes

The same repair patterns show up across categories:

- Replace sleeps and borderline deadlines with deterministic synchronization. Coder repeatedly fixed flakes by waiting for the actual state transition, passing explicit time values, using mock clocks, or widening time ranges only when the system genuinely depends on wall-clock latency.
- Scope shared state to the subtest. Contexts, transports, usernames, deployment handles, maps, mock clocks, and DB rows often leaked across parallel subtests.
- Make async teardown boring. Many flakes came from goroutines, websocket readers, provisioner jobs, or notification loops still running after the test had already asserted or cleaned up.
- Prefer local fakes over real external systems. Network, OpenAI, DNS, Docker, browser, and dependency-manager calls need either a fake, injected transport, or an explicit quarantine.
- Skips were used as containment, not cures. Several categories include skip/remove PRs. They usually bought time after repeated CI pain, while durable fixes changed synchronization, isolation, or resource budgets.
- Better flake discovery became part of the solution. Nightly/flake workflows and richer logs appear repeatedly because single CI failures lacked enough context.

## networking/proxy/websocket

Count: 105 rows, 65 issues, 40 PRs.

Common root cause pattern:
Transport tests observed distributed network state too early or assumed ideal delivery. Common failure modes include DERP messages getting lost, websocket closure racing with the reader, random ports being occupied, pings choosing a direct path when the test expected DERP, DNS lookup noise, WireGuard/devtunnel startup latency, and tailnet close paths racing with telemetry or waitgroups.

Recurring fixes Coder used:

- Replace real external routing with fake/local endpoints where possible. PR #3050 restored `devtunnel` tests with a fake local server.
- Retry inherently lossy exchanges or resource allocation. PR #7211 added retry around DERP exchange. PR #9746 retried tunnel server creation when the port was taken.
- Remove network-specific points of failure from tests. PR #10390 avoided DNS lookup as an extra GitHub Actions failure point for known test hosts.
- Synchronize lifecycle edges instead of relying on incidental timing. PR #6492 fixed buffered provisioner job log websocket closure so the client finished reading before close. PR #12760 waited for a workspace build to start before starting the agent in a SSH test.
- Fix actual concurrency bugs in transport code. Issue #1644 was fixed by PR #1774 and PR #3086 around peer negotiation/closing races. Issue #14143 was fixed by PR #14195 by locking tailnet waitgroup additions.
- Quarantine when the test is only breaking CI. PR #4081 skipped `TestPortForward`; PR #6322 skipped `TestSpeedtest`; PR #10826 skipped a flaky DERP healthcheck variant.

Examples:

- Issue #9107, PR #9262: `TestDERPHeaders` sometimes succeeded via P2P instead of DERP, so the expected DERP header path was not exercised.
- Issue #10832, PR #10833: listening ports tests saw stale or missing TCP port data during Linux/Windows agent observation.
- Issue #12277, PR #12280: `TestDERPEndToEnd` hit a nil DERP map region during websocket/proxy setup.
- Issue #13258, PR #13313: `TestIntegration/EasyNATDirect` was in the NAT/direct networking family.
- PR #6475: forced DERP websocket behavior was copied to reduce flake risk.
- PR #11541: `TestAgentWebsocketMonitor_SendPings` raced between observing a ping and storing `lastPing`.

Confidence: high. This is the largest category and has many linked fixes with specific technical causes.

Gaps:

- Some early `peer` and port-forward issues only have truncated run logs in the local metadata.
- Several fixes are skips or retries, so the durable product bug versus test-harness fragility split is not always clear without reading the full diff.

## workspace/agent lifecycle

Count: 102 rows, 44 issues, 58 PRs.

Common root cause pattern:
Tests assumed a workspace, agent, provisioner daemon, template version, PTY, reconnect path, or log stream had reached a terminal state before it had. The common shape is a lifecycle edge: build pending to running, provisioner complete to log drain, agent connect to metadata available, PTY command sent to output flushed, workspace stop to audit/build state settled.

Recurring fixes Coder used:

- Wait for the real lifecycle event before asserting. PR #9656 waited for the provisioner job to finish before updating template metadata. PR #10387 fixed `TestWorkspaceBuild` by aligning assertions with build state.
- Make terminal/job ordering explicit. PR #2732 changed provisionerd to send failed or complete last, narrowing the race from issue #2603. PR #2783 fixed the pubsub/poll race on provisioner job logs.
- Make PTY and agent tests less brittle about stream chunks. PR #1141 increased the `ptytest` buffer after data was discarded. PR #1562 stopped assuming a PTY command would echo back in one specific shape.
- Move source of truth to the object that owns it. PR #4333 moved workspace status to the workspace build, exposing a canceled-state bug.
- Improve instrumentation when the root cause is not visible. PR #5353 added logging around provisionerd flakes.
- Skip/load-test quarantine for persistent CI blockers. PR #4998 disabled a flaky load test. PR #5160 skipped reconnect-and-complete while issue #5159 remained unresolved.

Examples:

- Issue #382, PR #383: provisionerd panic flake.
- Issue #1368, PR #1562: `TestWorkspaceAgentPTY` reruns succeeded after the first failure, pointing to PTY/test sequencing fragility.
- Issue #2603, PRs #2732, #2783, #5353: job logs could end before the final `Cleaning Up` line was observed.
- Issue #10335, PR #10387: `TestWorkspaceBuild` lifecycle assertion.
- PR #2456: wrote the server URL only after signal listening was ready.
- PR #10963 and PR #10965: workspace autobuild/dormancy tests raced provisioner/audit-log behavior.

Confidence: high. There are many merged PRs with concrete lifecycle explanations.

Gaps:

- Several workspace lifecycle fixes touch broad test helpers, so the category sometimes overlaps with concurrency and timing.
- Some fixes state only a failing run URL with little postmortem text.

## concurrency/race

Count: 74 rows, 35 issues, 39 PRs.

Common root cause pattern:
Shared mutable state was accessed from multiple goroutines or parallel subtests without sufficient ordering. Recurrent signals include Go race detector failures, `Fail in goroutine after Test... has completed`, waitgroup add/close races, context cancellation racing success, shared maps, shared test-case structs, notification loops, file watchers, and singleflight/heartbeat checks.

Recurring fixes Coder used:

- Add or extend locking around shared state. PR #14167 extended locking in `wsproxy`. PR #14195 locked waitgroup additions in tailnet.
- Move checks inside the critical section or singleflight boundary. PR #8613 moved `lastCollectedAts` checks to avoid duplicate metadata collection.
- Scope errors and state to each subtest. PR #3765 scoped errors to test functions to fix `TestFeaturesService_EntitlementsAPI`.
- Remove incorrect synchronization primitives or replace them with simpler polling. PR #13944 replaced a naive `sync.Cond` pattern in pending update metrics.
- Avoid parallelism when the code under test is not concurrent. PR #14233 ran `Test_sshConfigExecEscape` subtests sequentially.
- Run high-count or race-detector repros to verify. PR #9709 reports `go test -race -count=10000 -run TestProvisionerd/InstantClose` after fixing issue #9340.
- Temporarily disable a test when the code has a suspected race but the fix is not ready. PR #10711 disabled `TestSSH/RemoteForward_Unix_Signal`.

Examples:

- Issue #3747, PR #3765: race detector failure in `TestFeaturesService_EntitlementsAPI`.
- Issue #4607, PR #4842: `TestReplica/TwentyConcurrent` failed under pegged CPU conditions.
- Issue #9340, PR #9709: goroutine called `Fail` after `TestProvisionerd/InstantClose` completed.
- Issue #14143, PR #14195: tailnet close raced with remote-forward telemetry.
- PR #13607: map read/write race in app health tests.
- PR #17441: parallel role-sync tests shared maps in test-case definitions.

Confidence: high. The category has explicit race-detector output and direct fixes.

Gaps:

- A few PRs classify as concurrency because they contain race language, but the actual durable fix may be test isolation or lifecycle sequencing.
- Some older race fixes have terse bodies and require diff reading for exact mechanics.

## database/transactions/migrations

Count: 47 rows, 15 issues, 32 PRs.

Common root cause pattern:
Database-backed tests failed due to shared Postgres resources, cleanup gaps, socket/port leaks, transaction timing, migration/tooling differences, concurrent deployment usage, or DB time precision. Some rows are DB-specific; others are tests whose DB dependency amplified a timing or isolation problem.

Recurring fixes Coder used:

- Serialize or protect shared DB-adjacent resources. PR #389 added a mutex to opening PostgreSQL ports to prevent collision.
- Clean up one-shot databases and leaked sockets. PR #2413 fixed socket leaks and cleaned up single-use Postgres databases.
- Use direct DB setup where API-level creation introduces races. PR #10992 used the database for user creation to prevent a flake.
- Create contexts per subtest. PR #15314 fixed a flake by scoping context per subtest.
- Avoid concurrent use of a shared deployment. PR #12700 fixed a flake caused by concurrent usage of the same deployment in workspace app tests.
- Reduce platform-specific Postgres stress. PR #15629 fixed more flaky Windows Postgres tests; PR #16090 later reduced Windows PG test parallelism in CI.
- Skip narrow, high-noise tests when root cause is not worth ongoing CI breakage. PR #12517 skipped a flaky DAU test, linked from issue #12509.

Examples:

- Issue #388, PR #389: PostgreSQL Docker port allocation collision.
- Issue #2347, PR #2413: mass `test/go/postgres` timeouts; cleanup and socket leaks were suspected and fixed.
- PR #8369: `TestUserLastSeenFilter` DB flake.
- PR #10222: `TestServerDBCrypt` enterprise CLI flake.
- PR #11384: `dbfake` PQ `TestStart_Starting` flake.
- PR #15629: Windows with Postgres flakes.

Confidence: medium-high. Many PRs are concrete, but this category overlaps heavily with platform and timing.

Gaps:

- Some DB rows are categorized from files touched rather than a full root-cause writeup.
- The corpus does not always distinguish DB semantics from DB-backed async lifecycle behavior.

## browser/e2e/playwright

Count: 47 rows, 15 issues, 32 PRs.

Common root cause pattern:
Frontend tests asserted against transient UI state, ambiguous selectors, unflushed React state, browser dependency availability, Storybook timing, or real app navigation before the page settled. E2E flakes often manifested as timeouts, too many element matches, target closed, or waiting for a selector that never reached the expected state.

Recurring fixes Coder used:

- Make selectors and assertions more specific. PR #10553 stopped `SSHKeysPage` from matching too many elements.
- Isolate test setup/teardown and mocks. PR #13250 updated `useClipboard` tests to improve teardown, mock timeout handling, and `describe.each` isolation.
- Wait for stable UI state rather than transient URLs or immediate DOM shape. PR #23655 fixed a flaky template update E2E test that expected a transient redirect URL.
- Reduce Storybook/browser flakiness with targeted waits or setup changes. PRs #14269, #15380, #17427, and #17450 all reduced Storybook flakes.
- Remove or skip tests that are not pulling their weight. PR #3207 removed a flaking test; PR #5884 removed a flaking E2E test; PR #19308 skipped a flaking classic parameters test.
- Provide required browser dependencies through the environment. PR #11974 added Google Chrome to the Nix flake for scale tests.

Examples:

- Issue #10481, PR #10553: `SSHKeyPage.test.tsx` matched too many elements.
- Issue #13240, PR #13250: `useClipboard` tests did not consistently flush state changes.
- Issue #5309: `WorkspacePage` exceeded a 5000ms Jest timeout.
- Issue #9424: `createWorkspace.spec.ts` timed out waiting for a selector.
- PR #9798: terminal page test flakiness.
- PR #16331: flaky IDP E2E tests.

Confidence: medium-high. Linked examples are strong, but many frontend PRs have brief bodies.

Gaps:

- Local metadata often lacks Playwright traces/screenshots, so selector and navigation fixes are inferred from PR titles and files.
- Some frontend rows are actually external-service or CI-environment issues, not browser logic.

## timing/eventual consistency

Count: 46 rows, 15 issues, 31 PRs.

Common root cause pattern:
Tests checked asynchronous state before the system converged or compared wall-clock values too tightly. This includes metrics/insights aggregation, notification state, labels/deployment stats, cache flushes, autostart/autostop scheduling, timezone boundaries, and code that calls `time.Now()` more than once around a boundary.

Recurring fixes Coder used:

- Pass explicit time values instead of sampling the clock twice. PR #11023 passed a time parameter; PR #19450 fixed a flake caused by two `time.Now()` calls.
- Use deterministic or mock clocks. PR #21396 used deterministic time to avoid a time-based flake. PR #23830 fixed a schedule override race near a UTC half-hour boundary.
- Poll for the actual condition with appropriate intervals. PR #8576 increased wait times in `testutil`; PR #22740 waited through the real template-version polling path.
- Align assertions with asynchronous cleanup. PR #23448 stabilized auto-promotion by waiting for cleanup/promotion to finish. PR #23816 stabilized queued chat tests by handling wake-loop timing.
- Widen borderline thresholds when the product genuinely measures elapsed time. PR #6350 increased activity bump deadline duration. PR #20447 fixed an SSH metrics test where startup scripts exceeded one second in CI.
- Skip temporarily when signal is too noisy. PR #12517 skipped the flaky DAU test from issue #12509.

Examples:

- Issue #12509, PR #12517: insights DAU response differed due to timing/timezone aggregation.
- Issue #3420: `TestServer/Prometheus` asserted before metric availability.
- Issue #5323: workspace prometheus metrics did not appear within the expected window.
- Issue #6481: `TestTemplateMetrics` was disabled because it flaked in full-suite runs.
- PR #12377: `Test_parseInsightsStartAndEndTime` time parsing flake.
- PR #22639: user status count timezone boundary flake.

Confidence: high. PR bodies repeatedly name clock, wait, poll, and boundary mechanics.

Gaps:

- Some fixes widen waits without proving the underlying event dependency, so they may be mitigation rather than root-cause repair.
- Metrics and cache rows overlap with workspace lifecycle and database categories.

## not-a-test-flake/nix-flake-or-maintenance

Count: 41 rows, 3 issues, 38 PRs.

Common root cause pattern:
These are search false positives for nondeterministic test flakes. They mostly involve `flake.nix`, `flake.lock`, `update-flake`, pinned tool versions, missing devshell tools, cross-platform Nix support, or automation around dependency updates.

Recurring fixes Coder used:

- Update `flake.lock` for changed toolchain behavior. PR #6173 fixed Go build problems by updating the lockfile. PRs #8226, #8645, and #8715 updated sqlc-related inputs.
- Add missing tools to `flake.nix`. PRs #9197, #9202, #9215, #9219, #9224, #11974, and #14728 added tools such as gcloud, kubectl, Sapling, kubectx, Chrome, and protoc-gen-go support.
- Make Nix work across platforms. PR #10591 handled macOS missing `strace`; PR #13930 handled aarch64 Linux where Google Chrome is unavailable.
- Automate lockfile refresh and tune its CI behavior. PRs #14046, #14052, #14067, #14091, #14552, and #14554 worked through update-flake workflow behavior.
- Fix update scripts. PR #13243 fixed a `sed` command in `scripts/update-flake.sh`.

Examples:

- Issue #7834: requested a Coder package derivation in the Nix flake.
- Issue #14343: wanted flake and GitHub Actions dependency versions aligned.
- Issue #26127: `google-chrome-stable_138.0.7204.49` disappeared from Google's CDN.
- PR #11716: made Yarn from the Nix flake use the right Node version.
- PR #13186: added Nix build targets.
- PR #14554: disabled update-flake in PRs.

Confidence: high for classification, low for test-flake relevance. These rows are intentionally excluded from flake-fix conclusions.

Gaps:

- None needed for test flake synthesis; the main gap is filtering these out earlier if the goal is only nondeterministic tests.

## platform/os-specific CI behavior

Count: 31 rows, 5 issues, 26 PRs.

Common root cause pattern:
Tests depended on OS-specific process, filesystem, clock, network, shell, PTY, dependency, or runner behavior. Windows, macOS/Darwin, ARM64, zsh, slow CI, and smaller runners all appear. Often the product code was fine on Linux but the test harness assumed Linux semantics.

Recurring fixes Coder used:

- Add platform-specific implementations or helpers. PR #21874 used an `os.Pipe` implementation for Windows CLI tests instead of creating a ConPTY with no process.
- Increase or normalize timeouts for slower CI/OSes. PR #1001 handled slow GitSSH CI runs. PR #21725 increased a Windows GitSSH timeout. PR #16090 unified wait intervals and reduced Windows PG parallelism.
- Skip tests on platforms where the behavior is not core or reliable. PR #4987 skipped a Windows UDP dial flake. PR #8652 skipped a flaky timezone test under Windows. PR #21897 dropped Windows for `TestGetModulesArchive` because Coder mostly runs in Linux containers.
- Remove OS-specific external dependencies or noise. PR #1026 handled noisy Datadog agent logs. PR #436 fixed yarn dependency install timeouts on macOS.
- Adjust assertions for platform time precision. Issue #14877 and PR #14888 removed a redundant API key refresh test likely affected by DB time precision.
- Fix shell/installer assumptions. PR #2309 addressed flaky `install.sh` upgrade on OSX/zsh.

Examples:

- Issue #998: Windows `test/go` job flakes.
- Issue #10202: scale test failure on Darwin ARM64.
- Issue #11239: `TestTunnel` unknown failure on Windows.
- Issue #14877, PR #14888: `TestAPIKey_Refresh` flaked due to very close timestamp comparisons.
- PR #410: macOS PTY flake when reading after command exit.
- PR #5776: time range check flaked on macOS.

Confidence: medium-high. Platform labels and PR titles are strong; exact root causes vary.

Gaps:

- Several platform issues were closed as no longer happening or skipped, not deeply diagnosed.
- Some old GitHub run URLs may no longer preserve logs.

## unknown/needs manual read

Count: 25 rows, 1 issue, 24 PRs.

Common root cause pattern:
The local metadata was insufficient to assign a reliable failure mode. The visible fixes still hint at familiar causes: context cancellation, wrong IDs, unordered audit logs, stale notifications, missing CI tools, Coder workspace environment leakage, and broad flake-detection workflow changes.

Recurring fixes Coder used:

- Handle acceptable context errors explicitly. PR #7119 handled filter flakes with context errors. PR #9865 checked context in log sender.
- Correct test expectations or IDs. PR #18311 fixed a dynamic parameters flake caused by waiting on the wrong build ID.
- Do not assume ordering when the system does not guarantee it. PR #11521 fixed a workspace update test where audit log ordering was not guaranteed.
- Sanitize environment assumptions. PRs #17604 and #17772 fixed CLI/MCP tests that failed inside a Coder workspace because workspace env vars were present.
- Add flake infrastructure. PR #7803 added a nightly flake workflow. PR #20368 and PR #20379 updated flake-bot workflow identity. PR #25934 installed `gotestsum` in the flake check workflow.
- Skip stale/noisy tests until semantics are improved. PR #25177 skipped chatd stale notification flakes with TODOs.

Examples:

- Issue #14151: `TestUpdateUserProfile/UpdateSelfAsMember` failed with unexpected 400, but local metadata lacks a linked fix.
- PR #2343: deadline-extension test was too borderline on slower platforms.
- PR #9666: `TestDeleteTemplate/NoWorkspaces` matched a known prior root cause but the local row lacks detail.
- PR #10875: fixed more instances of a templates test flake pattern in the same file.
- PR #17183: MCP test flakes.
- PR #24112: connection log batcher flush retries on transient failure.

Confidence: low by definition. Treat this section as leads, not conclusions.

Gaps:

- Manual reading of full PR discussions and linked internal issues is required.
- Several examples reference `coder/internal` issues unavailable in this corpus.

## resource exhaustion/timeout

Count: 21 rows, 14 issues, 7 PRs.

Common root cause pattern:
CI or tests exceeded resource budgets: wall-clock deadline, context timeout, CPU saturation, OOM, PTY exhaustion, package/test parallelism too high for the runner, or slow startup scripts. Some apparent network flakes were really resource starvation under CI load.

Recurring fixes Coder used:

- Reduce CI parallelism to fit runner capacity. PR #26009 reduced `flake-go` parallelism for a 4-vCPU runner after worst-case 64 in-flight subtests OOMed.
- Increase a budget only when the operation legitimately needs it. PR #10066 increased `ForceCancelInterval`. PR #20447 handled startup scripts taking longer than one second in CI.
- Scope contexts per subtest to prevent one timeout from poisoning siblings. PR #18872 fixed prebuilt workspace delete by giving subtests their own context.
- Remove expensive or flaky round-trips. PR #23877 removed OpenAI reasoning/web-search round-trip integration tests.
- Replace fragile real resources with deterministic fakes where possible. PR #3050 restored devtunnel with a fake local server.
- Investigate runner-level resource limits. PR #21981 and PR #22147 addressed PTY exhaustion in parallel tests.

Examples:

- Issue #2335, PR #3050: `TestTunnel` hit context deadline exceeded; restored with fake local server.
- Issue #5187: reconnecting PTY load test burned CI cycles and produced connection closed errors.
- Issue #5343: workspace app proxy path deadline exceeded.
- Issue #8968: workspace watcher timed out waiting for an event.
- PR #22883: Windows GitSSH local keys timed out in setup and client request paths.
- PR #26009: explicit CPU/OOM parallelism fix in `flake-go` workflow.

Confidence: medium. Resource failures are visible, but they frequently mask lifecycle, networking, or platform causes.

Gaps:

- Many issue rows have no linked fix, so root cause may remain speculative.
- CI logs with actual memory/CPU pressure are not in the local corpus.

## test isolation/order dependency

Count: 20 rows, 5 issues, 15 PRs.

Common root cause pattern:
Tests reused state that should have been unique: usernames, ports, temp paths, generated credentials, contexts, HTTP transports, deployments, mock providers, or global environment. Parallel execution and random ordering then exposed collisions or teardown races.

Recurring fixes Coder used:

- Generate unique data per test. PR #11501 generated a new random username. PR #6116 increased generated password length. PR #8002 removed brittle Git SSH key comparison when weak randomness generated the same key.
- Guard command and port lifetimes. PR #1650 guarded against a CLI command running after test exit and against port reuse from parallel tests.
- Avoid parallel subtests for non-concurrent behavior. PR #14233 ran `Test_sshConfigExecEscape` sequentially.
- Centralize harness setup to isolate external providers. PR #25171 centralized the chat test harness and stopped background title generation from reaching `api.openai.com`.
- Inject failing transports rather than depending on closing servers. PR #26132 made `TestResolveWorkspace/TransportError` deterministic with a failing `http.RoundTripper`.
- Add flake-detection workflows for order/race hunting. PR #25667 added the Go test flake detector workflow.

Examples:

- Issue #2709, PR #2730: duplicate user names caused `TestUsersFilter` 409 conflicts.
- Issue #13962, PR #14233: temp/path collision theory in parallel `Test_sshConfigExecEscape` subtests.
- PR #6494: workspace audit log flake when a build queued/completed intermittently.
- PR #9680: cleanup ran while a provisioning job was still in progress.
- PR #25630: async recorded token usage could appear in different order.
- PR #26132: closing test server sometimes returned 404 instead of the desired transport error.

Confidence: medium-high. The examples have crisp fixes, but this category is small.

Gaps:

- Some rows overlap with concurrency and timing; isolation is often the test-harness expression of those deeper causes.
- Several issue rows lack linked fixes.

## external service/dependency

Count: 4 rows, 2 issues, 2 PRs.

Common root cause pattern:
Tests depended on outside services or globally shared dependency clients. Failures came from OpenAI round-trips, shared `http.DefaultTransport`, package/CDN availability, Docker/setup actions, or browser/dependency installs.

Recurring fixes Coder used:

- Remove real external service calls from CI tests. PR #23877 removed flaky OpenAI reasoning plus web-search round-trip integration tests.
- Give parallel tests isolated clients/transports. PR #25015 used separate HTTP clients/transports because `httptest.Server.Close()` closed idle connections on a shared default transport used by sibling subtests.
- Add missing dependencies to reproducible environments. PR #11974 added Google Chrome to the Nix flake for scale/browser tests.
- Treat vanished upstream artifacts as maintenance, not test flakes. Issue #26127 records a Google Chrome CDN 404 for the Nix package.

Examples:

- Issue #10105: workspace schedule page frontend test interacted with testing-library waits and likely UI dependency timing.
- Issue #14535: `UsersPage.test.tsx` failed around testing-library/user-event interaction.
- PR #23877: removed OpenAI round-trip tests.
- PR #25015: isolated external auth token validation transports.

Confidence: medium. The category is tiny, but PR #23877 and PR #25015 are very clear.

Gaps:

- Too little data for broad conclusions.
- Frontend dependency flakes are split between this category and browser/e2e/playwright.

## Practical fix playbook

When a new Coder flake appears, the historical fixes suggest this order:

1. Identify whether the failure is a real product race or a test harness assumption. Race detector output, goroutine-after-test panics, and shared maps point to product or helper concurrency first.
2. Replace sleep/deadline guesses with an observable state transition. If the test needs a workspace build, provisioner log, websocket ping, metric sample, or UI navigation, wait for that exact thing.
3. Scope every mutable dependency to the subtest: context, database rows, usernames, transports, fake providers, temp paths, mock clocks, and deployments.
4. Remove real external systems from unit/integration tests. Inject transports, fake servers, deterministic DNS/HTTP behavior, and local providers.
5. Check platform and resource budgets before widening waits. Windows/macOS/ARM64 and 4-vCPU runners may need separate helpers or lower parallelism, not more sleeps.
6. If the root cause is still opaque, add targeted logging or a flake detector run before merging a blind timeout bump.
7. Skip only as a containment measure, and leave a clear issue/TODO when the test still matters.
