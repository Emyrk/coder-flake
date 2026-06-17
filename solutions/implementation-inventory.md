# Flake finding implementation inventory

This tracks the static flake findings from `solutions/*.md` against implementation branches and blockers.

## Open PRs

| Finding | Branch | PR | Status |
|---|---|---:|---|
| `provisioner/terraform/install_test.go` background goroutine assertions | `flake-fix/terraform-install` | https://github.com/Emyrk/coder/pull/1 | opened |
| `pty/start_test.go` background goroutine assertions | `flake-fix/pty-truncation` | https://github.com/Emyrk/coder/pull/2 | opened |

## In-progress local branches

| Finding | Branch | Files | Status | Notes |
|---|---|---|---|---|
| `enterprise/coderd/workspacequota_test.go` worker assertions | `flake-fix/workspacequota-workers` | `enterprise/coderd/workspacequota_test.go` | commit hook running | Focused `TestWorkspaceQuota/CreateDelete` passed. Full `TestWorkspaceQuota` hit an existing `MultiOrg` context deadline unrelated to the edited subtest. |
| `coderd/database/pubsub` goroutine assertions and msg queue callback assertions | `flake-fix/pubsub-goroutine-assertions` | `coderd/database/pubsub/pubsub_linux_test.go`, `coderd/database/pubsub/pubsub_test.go` | needs cleanup | Focused tests passed individually. Combined repeated run exposed pre-existing `TestPubsub_Disconnect` fixed-port conflict and `TestPubsub_ordering` random sleep timeout. |
| `testutil/expecter` stdbuf goroutine assertion | `flake-fix/stdbuf-copy` | `testutil/expecter/stdbuf_internal_test.go` | needs commit retry | Focused `go test ./testutil/expecter -run TestStdbuf -count=20` passed. Commit hook was blocked by unrelated golden test flakes and generated-file churn. |
| `cli/task_logs_test.go` golden log serialization | `flake-fix/task-logs-golden-serial` | `cli/task_logs_test.go` | needs review | Local diff exists but has not been verified in this handoff window. |

## Finding inventory from reports

1. Fixed sleeps hide readiness in organization and IdP selector flows, `browser-e2e-playwright.md`.
2. `DynamicParameter` tests wrap `userEvent` in retry loops with no assertion, `browser-e2e-playwright.md`.
3. Parallel template update specs share a non-unique template name, `browser-e2e-playwright.md`.
4. E2E web server depends on real Google OIDC discovery, `browser-e2e-playwright.md`.
5. Background goroutines call test assertions and test helpers, `concurrency-resource-timeout.md`.
6. Resource-heavy fanout runs inside normal tests without a local budget, `concurrency-resource-timeout.md`.
7. Sleeps are used as readiness or quiet-period synchronization, `concurrency-resource-timeout.md`.
8. Long-running goroutines and servers are closed but not always joined, `concurrency-resource-timeout.md`.
9. Timeout failures would lack last-observed state or runner context in several high-risk tests, `concurrency-resource-timeout.md`.
10. Pubsub tests call `require` from goroutines, `database-transactions-migrations.md`.
11. Pubsub ordering test depends on random goroutine sleep ordering, `database-transactions-migrations.md`.
12. Metrics expiry test relies on wall-clock sleep and polling, `database-transactions-migrations.md`.
13. Purge tests compare database timestamps for exact equality, `database-transactions-migrations.md`.
14. DB metrics transaction test asserts raw log text after mocked retry state, `database-transactions-migrations.md`.
15. Assertions run inside workspace traffic goroutines, `networking-proxy-websocket.md`.
16. Workspace proxy timestamp boundary relies on a 1 ms sleep, `networking-proxy-websocket.md`.
17. Tailnet pgcoord test uses sleep to prove absence of async work, `networking-proxy-websocket.md`.
18. Tailnet connection test waits 10 seconds for absence of disco endpoints, `networking-proxy-websocket.md`.
19. Provisionerd reconnect path uses a fixed sleep as a sequencing barrier, `workspace-agent-lifecycle.md`.
20. Provisioner acquirer test intentionally races pubsub processing with DB return, `workspace-agent-lifecycle.md`.
21. Workspace build helper may return after job completion but before dependent side effects are visible, `workspace-agent-lifecycle.md`.
22. Startup log writer test has unsynchronized shared capture in parallel subtests, `workspace-agent-lifecycle.md`.
23. Boundary log proxy tests assert counts, then cancel the forwarder without a drained/closed acknowledgement, `workspace-agent-lifecycle.md`.
24. Agent metadata timing test uses real elapsed time as the assertion oracle, `workspace-agent-lifecycle.md`.
