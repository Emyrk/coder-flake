# Synthesized potential flakes

## Scope

This report synthesizes the area audits already written under `/home/openclaw/coder-flake-research/solutions/` for the current `/home/openclaw/coder` checkout.

Inputs read:

- `solutions/networking-proxy-websocket.md`
- `solutions/workspace-agent-lifecycle.md`
- `solutions/concurrency-resource-timeout.md`
- `solutions/browser-e2e-playwright.md`
- `solutions/database-transactions-migrations.md`
- `ONE_PAGER.md`
- Relevant taxonomy pages under `categories/`
- `notes/common-solutions.md`
- `notes/proposed-solutions.md`
- `flake-audit/references/patterns.md`
- `/home/openclaw/coder/AGENTS.md`
- `/home/openclaw/coder/.claude/docs/TESTING.md`

These are potential flakes from static audit. They are not confirmed bugs unless reproduced with repeated runs, race detector output, CI evidence, or a targeted failing artifact.

## Files inspected

The synthesis did not rescan `/home/openclaw/coder`. It read the five area reports and preserved their evidence. Those reports inspected these high-signal areas:

- `scaletest/workspacetraffic/run_test.go`
- `enterprise/coderd/workspaceproxy_test.go`
- `enterprise/tailnet/pgcoord_internal_test.go`
- `tailnet/conn_test.go`
- `provisionerd/provisionerd_test.go`
- `coderd/provisionerdserver/acquirer_test.go`
- `coderd/coderdtest/coderdtest.go`
- `coderd/workspacebuilds_test.go`
- `codersdk/agentsdk/logs_test.go`
- `agent/boundarylogproxy/proxy_test.go`
- `agent/agent_test.go`
- `pty/start_test.go`
- `enterprise/coderd/workspacequota_test.go`
- `provisioner/terraform/install_test.go`
- `coderd/activitybump_test.go`
- `coderd/templates_test.go`
- `cli/server_test.go`
- `aibridge/internal/integrationtest/circuit_breaker_internal_test.go`
- `enterprise/coderd/prebuilds/reconcile_test.go`
- `agent/agentproc/api_test.go`
- `site/e2e/playwright.config.ts`
- `site/e2e/tests/organizations.spec.ts`
- `site/e2e/tests/organizations/idpGroupSync.spec.ts`
- `site/e2e/tests/organizations/idpRoleSync.spec.ts`
- `site/e2e/tests/deployment/idpOrgSync.spec.ts`
- `site/e2e/tests/templates/updateTemplateSchedule.spec.ts`
- `site/e2e/tests/updateTemplate.spec.ts`
- `site/src/modules/workspaces/DynamicParameter/DynamicParameter.test.tsx`
- `coderd/database/pubsub/pubsub_linux_test.go`
- `coderd/database/pubsub/pubsub_test.go`
- `coderd/prometheusmetrics/aggregator_test.go`
- `coderd/database/dbpurge/dbpurge_test.go`
- `coderd/database/dbmetrics/dbmetrics_test.go`

See each area report for the complete inspected-file list.

## Findings

### 1. Assertions and testing helpers run from background goroutines

- Category: `concurrency/race`, with overlaps in `resource exhaustion/timeout`, `networking/proxy/websocket`, and `database/transactions/migrations`.
- Evidence:
  - `solutions/networking-proxy-websocket.md`: `/home/openclaw/coder/scaletest/workspacetraffic/run_test.go:116-126`, `:236-246`, `:336-346`.
  - `solutions/concurrency-resource-timeout.md`: `/home/openclaw/coder/pty/start_test.go:68-91`, `/home/openclaw/coder/enterprise/coderd/workspacequota_test.go:154-161`, `/home/openclaw/coder/provisioner/terraform/install_test.go:142-149`, `/home/openclaw/coder/enterprise/coderd/prebuilds/reconcile_test.go:1976-2004`.
  - `solutions/database-transactions-migrations.md`: `/home/openclaw/coder/coderd/database/pubsub/pubsub_linux_test.go:113-125`, `/home/openclaw/coder/coderd/database/pubsub/pubsub_test.go:272-283`.
- Why it can flake: `require.*`, `assert.*`, and helpers that take `testing.TB` can fail in the wrong goroutine. The parent test may keep running, cleanup may race the worker, or the failure may surface late as `Fail in goroutine after Test... has completed`.
- Proposed fix: Return worker errors and values through channels or `errgroup.Group`. Join workers before cleanup. Assert only from the parent test goroutine.
- Validation:
  - `cd /home/openclaw/coder && go test -race -count=100 ./scaletest/workspacetraffic -run TestRun`
  - `cd /home/openclaw/coder && go test -race -count=100 ./pty -run Test_Start_truncation`
  - `cd /home/openclaw/coder && go test -race -count=100 ./enterprise/coderd -run TestWorkspaceQuota`
  - `cd /home/openclaw/coder && go test -race -count=100 ./provisioner/terraform -run TestInstall`
  - `cd /home/openclaw/coder && go test -race -count=100 ./enterprise/coderd/prebuilds -run TestReconciliationLock`
  - `cd /home/openclaw/coder && go test ./coderd/database/pubsub -run 'TestPubsub_ordering|Test_MsgQueue_Full' -count=100 -race`
- Historical references: `categories/concurrency-race.md` cites issue #9340 and PR #9709 for goroutine failure after `TestProvisionerd/InstantClose` completed. `notes/proposed-solutions.md` recommends test helpers that never call `t.Fatal` from non-test goroutines.

### 2. Fixed sleeps stand in for lifecycle, readiness, or absence barriers

- Category: `timing/eventual consistency`, with overlaps in `workspace/agent lifecycle`, `networking/proxy/websocket`, `browser/e2e/playwright`, `database/transactions/migrations`, and `resource exhaustion/timeout`.
- Evidence:
  - `solutions/networking-proxy-websocket.md`: `/home/openclaw/coder/enterprise/coderd/workspaceproxy_test.go:458`, `:468`; `/home/openclaw/coder/enterprise/tailnet/pgcoord_internal_test.go:432-437`; `/home/openclaw/coder/tailnet/conn_test.go:456-458`.
  - `solutions/workspace-agent-lifecycle.md`: `/home/openclaw/coder/provisionerd/provisionerd_test.go:940-947`; `/home/openclaw/coder/coderd/provisionerdserver/acquirer_test.go:194-200`.
  - `solutions/concurrency-resource-timeout.md`: `/home/openclaw/coder/cli/server_test.go:335-341`; `/home/openclaw/coder/coderd/activitybump_test.go:210-216`, `:248-254`; `/home/openclaw/coder/coderd/templates_test.go:912-920`; `/home/openclaw/coder/aibridge/internal/integrationtest/circuit_breaker_internal_test.go:463-465`.
  - `solutions/browser-e2e-playwright.md`: `/home/openclaw/coder/site/e2e/tests/organizations.spec.ts:51-56`, `/home/openclaw/coder/site/e2e/tests/organizations/idpGroupSync.spec.ts:161-170`, `/home/openclaw/coder/site/e2e/tests/organizations/idpRoleSync.spec.ts:138-152`, `/home/openclaw/coder/site/e2e/tests/deployment/idpOrgSync.spec.ts:158-167`.
  - `solutions/database-transactions-migrations.md`: `/home/openclaw/coder/coderd/database/pubsub/pubsub_linux_test.go:104-146`, `/home/openclaw/coder/coderd/prometheusmetrics/aggregator_test.go:260-306`.
- Why it can flake: Sleep durations encode timing guesses. They can be too short under CI load and still fail to prove the event, absence, or quiet period the test actually needs.
- Proposed fix: Replace sleeps with exact readiness signals, drains, fake clocks, deterministic test hooks, or `Eventually` loops that report the last observed state. For absence assertions, wait for an explicit idle or drained state before asserting no work occurred.
- Validation:
  - `cd /home/openclaw/coder && go test ./enterprise/coderd -run TestWorkspaceProxy -count=100`
  - `cd /home/openclaw/coder && go test -race ./enterprise/tailnet -run Test.*PgCoord -count=25`
  - `cd /home/openclaw/coder && go test -race ./tailnet -run TestConn -count=25`
  - `cd /home/openclaw/coder && go test ./provisionerd -run 'TestProvisionerd/.*/ReconnectAndFail' -count=100 -race`
  - `cd /home/openclaw/coder && go test ./coderd/provisionerdserver -run '^TestAcquirer_RetriesPending$' -count=200 -race`
  - `cd /home/openclaw/coder/site && pnpm playwright:test e2e/tests/organizations.spec.ts e2e/tests/organizations/idpGroupSync.spec.ts e2e/tests/organizations/idpRoleSync.spec.ts e2e/tests/deployment/idpOrgSync.spec.ts --repeat-each=20 --workers=2`
  - `cd /home/openclaw/coder && go test ./coderd/prometheusmetrics -run TestUpdateMetrics_MetricsExpire -count=100 -race`
- Historical references: `categories/timing-eventual-consistency.md` recommends polling the actual condition and using injected clocks. `notes/common-solutions.md` names replacing sleeps with deterministic synchronization as a cross-category theme. PR #19450, PR #21396, and PR #23830 are representative time-boundary fixes.

### 3. Lifecycle helpers can return before dependent side effects settle

- Category: `workspace/agent lifecycle`, with overlaps in `timing/eventual consistency` and `database/transactions/migrations`.
- Evidence:
  - `solutions/workspace-agent-lifecycle.md`: `/home/openclaw/coder/coderd/coderdtest/coderdtest.go:1245-1268`, `/home/openclaw/coder/coderd/workspacebuilds_test.go:73-83`, `/home/openclaw/coder/coderd/coderdtest/coderdtest.go:1419-1437`.
  - `solutions/workspace-agent-lifecycle.md`: `/home/openclaw/coder/codersdk/agentsdk/logs_test.go:218-255`, `:379-415`.
  - `solutions/workspace-agent-lifecycle.md`: `/home/openclaw/coder/agent/boundarylogproxy/proxy_test.go:126-177`, `:204-229`, `:252-290`.
  - `solutions/workspace-agent-lifecycle.md`: `/home/openclaw/coder/agent/agent_test.go:1926-1964`.
- Why it can flake: Build completion, log counts, forwarder cancellation, and metadata count are not always full lifecycle barriers. Derived state can lag the first visible success field.
- Proposed fix: Keep narrow helpers narrow, but add named helpers for derived state: audit logs persisted, workspace resources visible, startup logs drained, boundary log forwarder idle, agent metadata collected, and app routes available. Timeout errors should include last observed state.
- Validation:
  - `cd /home/openclaw/coder && go test ./coderd -run 'TestWorkspaceBuild' -count=50 -race`
  - `cd /home/openclaw/coder && go test ./codersdk/agentsdk -run '^TestStartupLogsWriter_Write$' -count=200 -race`
  - `cd /home/openclaw/coder && go test ./agent/boundarylogproxy -run '^TestServer_(ReceiveAndForwardLogs|MultipleMessages|MultipleConnections)$' -count=200 -race`
  - `cd /home/openclaw/coder && go test ./agent -run '^TestAgent_Metadata' -count=100 -race`
- Historical references: `categories/workspace-agent-lifecycle.md` is the second-largest corpus bucket. It recommends exact lifecycle waits: build created, provisioner job started, job complete, logs drained, agent ready, app route available. Issue #2603 and PRs #2732, #2783, and #5353 cover provisioner log ordering and diagnostics.

### 4. Resource-heavy fanout and opaque timeouts amplify flakes

- Category: `resource exhaustion/timeout`, with overlaps in `workspace/agent lifecycle`, `database/transactions/migrations`, `platform/os-specific CI behavior`, and `concurrency/race`.
- Evidence:
  - `solutions/concurrency-resource-timeout.md`: `/home/openclaw/coder/enterprise/coderd/workspacequota_test.go:152-164`, `/home/openclaw/coder/provisioner/terraform/install_test.go:135-149`, `/home/openclaw/coder/enterprise/coderd/prebuilds/reconcile_test.go:1974-2007`.
  - `solutions/concurrency-resource-timeout.md`: `/home/openclaw/coder/provisioner/terraform/install_test.go:129-133`, `/home/openclaw/coder/cli/server_test.go:333-341`.
  - `solutions/concurrency-resource-timeout.md`: `/home/openclaw/coder/pty/start_test.go:61-64`, `:99-110`; `/home/openclaw/coder/enterprise/coderd/prebuilds/reconcile_test.go:1994-2004`.
- Why it can flake: Small fanout inside one test can become large when combined with package parallelism, race detector overhead, DB cost, PTYs, provisioners, or browser workers. Opaque timeout output then hides whether the failure was product behavior, cleanup ordering, or runner pressure.
- Proposed fix: Bound fanout with local budgets where concurrency itself is not the product behavior. When concurrency is the behavior, include last observed lifecycle state, lock holder/waiter counts, process state, command output, OS, CPU count, job name, and package parallelism in timeout failures. Join ad hoc servers before cleanup returns.
- Validation:
  - `cd /home/openclaw/coder && go test -race -count=100 -parallel=16 ./enterprise/coderd -run TestWorkspaceQuota`
  - `cd /home/openclaw/coder && go test -race -count=100 -parallel=16 ./enterprise/coderd/prebuilds -run TestReconciliationLock`
  - `cd /home/openclaw/coder && go test -race -count=100 -parallel=16 ./provisioner/terraform -run TestInstall`
  - `cd /home/openclaw/coder && go test -count=100 ./pty -run Test_Start_truncation`
  - `cd /home/openclaw/coder && go test -count=100 ./cli -run 'TestServer/SpammyLogs'`
- Historical references: `categories/resource-exhaustion-timeout.md` says timeouts are symptoms and recommends runner CPU, memory, job, package, and parallelism in failure output. PR #26009 reduced `flake-go` parallelism after 4-vCPU runner pressure produced OOM-like flakes.

### 5. Browser and frontend tests have false synchronization and shared identity risks

- Category: `browser/e2e/playwright`, `test isolation/order dependency`, `external service/dependency`, and `timing/eventual consistency`.
- Evidence:
  - `solutions/browser-e2e-playwright.md`: `/home/openclaw/coder/site/src/modules/workspaces/DynamicParameter/DynamicParameter.test.tsx:194-221`, `:277-279`, `:308-310`, `:349-351`, `:429-431`, `:526-533`, `:548-550`.
  - `solutions/browser-e2e-playwright.md`: `/home/openclaw/coder/site/e2e/tests/updateTemplate.spec.ts:13`, `/home/openclaw/coder/site/e2e/tests/templates/updateTemplateSchedule.spec.ts:26-29`, `/home/openclaw/coder/site/e2e/playwright.config.ts:44-49`.
  - `solutions/browser-e2e-playwright.md`: `/home/openclaw/coder/site/e2e/playwright.config.ts:151-158`.
- Why it can flake: Retrying user actions without an assertion can repeat clicks and mutate state twice. Fixed template names can collide under parallelism or retries. Real Google OIDC discovery can make PR CI depend on DNS, upstream availability, TLS, and rate limits.
- Proposed fix: Perform user actions once, then wait on observable UI state. Generate unique template names with the existing `randomName()` helper. Replace real OIDC discovery with a fake issuer, or document and quarantine it if intentionally remote.
- Validation:
  - `cd /home/openclaw/coder/site && pnpm test -- src/modules/workspaces/DynamicParameter/DynamicParameter.test.tsx --runInBand --repeat-each=20`
  - `cd /home/openclaw/coder/site && pnpm playwright:test e2e/tests/templates/updateTemplateSchedule.spec.ts e2e/tests/updateTemplate.spec.ts --repeat-each=20 --workers=4`
  - `cd /home/openclaw/coder/site && env -u HTTPS_PROXY -u HTTP_PROXY pnpm playwright:test e2e/tests/deployment e2e/tests/organizations --repeat-each=10 --workers=2`
- Historical references: `categories/browser-e2e-playwright.md` recommends stable selectors and settled UI state. PR #24480 removed redundant `waitFor` around `userEvent` in `CreateWorkspacePage.test.tsx`. `categories/external-service-dependency.md` classifies upstream DNS, auth providers, credentials, and latency as nondeterministic CI inputs.

### 6. DB-backed timing and timestamp assertions remain brittle

- Category: `database/transactions/migrations` and `timing/eventual consistency`.
- Evidence:
  - `solutions/database-transactions-migrations.md`: `/home/openclaw/coder/coderd/database/dbpurge/dbpurge_test.go:580-669`, especially `:619` and `:642`.
  - `solutions/database-transactions-migrations.md`: `/home/openclaw/coder/coderd/database/dbmetrics/dbmetrics_test.go:79-108`.
  - `solutions/networking-proxy-websocket.md`: `/home/openclaw/coder/enterprise/coderd/workspaceproxy_test.go:458`, `:468`.
  - `solutions/concurrency-resource-timeout.md`: `/home/openclaw/coder/coderd/templates_test.go:912-920`.
- Why it can flake: Exact timestamp equality and tiny timestamp gaps cross database precision, timezone normalization, monotonic clock stripping, and scheduler boundaries. Raw log text assertions add formatting brittleness around transaction retry state.
- Proposed fix: Normalize times to DB precision or use `require.WithinDuration` with a narrow documented delta. Prefer injected clocks for boundary tests. For transaction logs, assert structured fields or metrics instead of rendered human log text.
- Validation:
  - `cd /home/openclaw/coder && go test ./coderd/database/dbpurge -run 'Test.*Workspace.*App|Test.*Purge' -count=100`
  - `cd /home/openclaw/coder && go test ./coderd/database/dbmetrics -run TestInTxMetrics -count=100`
  - `cd /home/openclaw/coder && go test ./coderd -run 'TestPatchTemplateMeta/(Update|AGPL_Deprecated)' -count=100`
- Historical references: `categories/database-transactions-migrations.md` covers DB timestamp precision and transaction round trips. `notes/common-solutions.md` recommends precision-aware time comparisons. PR #1235, PR #17678, PR #19450, PR #21228, and PR #22491 are representative time or DB timestamp fixes.

## Clean patterns / non-findings

- No report recommends stale Go loop-variable capture fixes such as `tc := tc` solely for `t.Parallel()` range loops.
- The audits found existing good patterns: explicit lifecycle helpers in `coderdtest`, `goleak.Verify` in high-risk packages, Playwright screenshots/traces/videos on failure, local fake Git auth endpoints, and many tests that already use unique names.
- `context.WithTimeout` was not treated as a flake by itself. It became actionable only when combined with PTY/process/DB-lock hotspots and poor diagnostics.
- Some sleeps model product time directly. Those are still candidates for fake clocks, but the reports did not blanket-flag every `time.Sleep`.
- The synthesis intentionally does not add new `/home/openclaw/coder` findings beyond the five area reports.

## Next steps

1. Fix assertions from background goroutines first. This pattern appears in networking, concurrency, DB/pubsub, workspace quota, Terraform install, prebuild reconciliation, and PTY tests. It maps directly to prior Coder race flakes.
2. Replace fixed sleeps that control interleavings. Start with provisionerd reconnect, provisioner acquirer pubsub, workspace proxy timestamp boundary, pubsub ordering, metrics expiry, and the frontend selector waits.
3. Add or harden shared lifecycle helpers for build side effects, audit logs, startup log drains, boundary log proxy drains, agent metadata readiness, and app route readiness.
4. Add deterministic time support or precision-aware helpers for scheduling, activity bump, metrics expiry, template metadata, DB purge timestamps, and workspace proxy timestamps.
5. Right-size stress validation. Run targeted `-race -count=N` commands from the reports, not full-suite reruns, then promote only reproduced patterns into confirmed bug tickets.
6. Keep quarantine disciplined. If any test is skipped while fixing these, include owner, issue, category, date, and retirement condition.
