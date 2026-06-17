# database, transactions, pubsub, migrations potential flakes

## Scope

Audited potential nondeterministic test flakes in the current `github.com/coder/coder` checkout under `/home/openclaw/coder`, focused on database-backed tests and adjacent async DB state readers.

These are potential flakes, not confirmed bugs. I did not reproduce failures. Findings are based on line-level evidence, existing Coder flake taxonomy, and historical patterns from `/home/openclaw/coder-flake-research`.

## Files inspected

- `/home/openclaw/coder/coderd/database/pubsub/pubsub_linux_test.go`
- `/home/openclaw/coder/coderd/database/pubsub/pubsub_test.go`
- `/home/openclaw/coder/coderd/database/migrations/migrate_test.go`
- `/home/openclaw/coder/coderd/database/querier_test.go`
- `/home/openclaw/coder/coderd/database/dbauthz/customroles_test.go`
- `/home/openclaw/coder/coderd/database/dbpurge/dbpurge_test.go`
- `/home/openclaw/coder/coderd/database/dbmetrics/dbmetrics_test.go`
- `/home/openclaw/coder/coderd/database/dbtestutil/postgres_test.go`
- `/home/openclaw/coder/coderd/database/tx_test.go`
- `/home/openclaw/coder/coderd/agentapi/boundary_logs_test.go`
- `/home/openclaw/coder/coderd/workspaceapps/stats_test.go`
- `/home/openclaw/coder/coderd/prometheusmetrics/aggregator_test.go`

## Findings

### Pubsub tests call `require` from goroutines

- Category: concurrency/race
- Evidence:
  - `/home/openclaw/coder/coderd/database/pubsub/pubsub_linux_test.go:113` starts goroutines inside `TestPubsub_ordering`.
  - `/home/openclaw/coder/coderd/database/pubsub/pubsub_linux_test.go:116` calls `require.NoError(t, err)` from that goroutine.
  - `/home/openclaw/coder/coderd/database/pubsub/pubsub_linux_test.go:125` calls `require.NoError(t, ps.Publish(...))` from that goroutine.
  - `/home/openclaw/coder/coderd/database/pubsub/pubsub_test.go:272` starts a goroutine inside `Test_MsgQueue_Full`.
  - `/home/openclaw/coder/coderd/database/pubsub/pubsub_test.go:276` and `/home/openclaw/coder/coderd/database/pubsub/pubsub_test.go:283` call `require.Equal(t, ...)` from that goroutine.
- Why it can flake:
  - `require.*` uses `t.FailNow()`, which must run in the test goroutine. Calling it from a worker goroutine can terminate only that goroutine, leave the parent test waiting on channels, or race with test cleanup.
  - This matches the knowledge-base concurrency pattern for assertions from goroutines and goroutine-after-test cleanup issues.
- Proposed fix:
  - Move assertions back to the parent goroutine by sending structured results over a channel.
  - Use `assert.*` only if the goroutine can safely report failures and the parent drains the result, but prefer explicit `errCh` or `resultCh` plus parent-side `require`.
  - For `TestPubsub_ordering`, have each publisher goroutine send `error` values to `errCh`; wait for all goroutines, close `errCh`, then `require.NoError` in the parent.
  - For `Test_MsgQueue_Full`, send the consumed values to a channel and compare them after receiving in the parent goroutine.
- Validation:
  - `cd /home/openclaw/coder && go test ./coderd/database/pubsub -run 'TestPubsub_ordering|Test_MsgQueue_Full' -count=100 -race`
- Historical references:
  - `categories/concurrency-race.md`: goroutine-after-test and assertion-from-goroutine failures, including issue #9340 and PR #13209.
  - `processed/categories.csv`: pubsub flake history, including issues #11576, #12030, #13293 and PR #13301.

### Pubsub ordering test depends on random goroutine sleep ordering

- Category: timing/eventual consistency
- Evidence:
  - `/home/openclaw/coder/coderd/database/pubsub/pubsub_linux_test.go:104` assigns `randomTime := rand.Intn(100)`.
  - `/home/openclaw/coder/coderd/database/pubsub/pubsub_linux_test.go:117` sleeps with `time.Sleep(time.Duration(n) * time.Millisecond)` inside publisher goroutines.
  - `/home/openclaw/coder/coderd/database/pubsub/pubsub_linux_test.go:129` waits on a single `done` channel and `/home/openclaw/coder/coderd/database/pubsub/pubsub_linux_test.go:140` uses `testutil.WaitShort` as the test timeout.
  - `/home/openclaw/coder/coderd/database/pubsub/pubsub_linux_test.go:146` requires `res.Messages == int64(limit)`.
- Why it can flake:
  - The test intentionally randomizes publish timing and then expects all messages to arrive before a short timeout. On loaded CI, scheduler jitter, DB notification latency, or a slow listener can push completion past `WaitShort` even when behavior is correct.
  - Random sleeps make failed runs hard to reproduce because the seed and schedule are not captured.
- Proposed fix:
  - Replace random sleep ordering with deterministic orchestration. For example, start all goroutines behind a barrier, publish deterministic IDs, and collect until the expected count using a context with a captured diagnostic timeout.
  - If randomness is valuable, log the seed and use a longer stress-test-only path outside the normal unit test.
  - Avoid `WaitShort` for DB/pubsub delivery tests; use the standard Coder wait profile for DB-backed async work and emit diagnostics on timeout.
- Validation:
  - `cd /home/openclaw/coder && go test ./coderd/database/pubsub -run TestPubsub_ordering -count=100 -race`
- Historical references:
  - `categories/timing-eventual-consistency.md`: fixed sleeps and timeout-sensitive async assertions.
  - `processed/categories.csv`: pubsub notification flakes, including issues #11576, #12030, #13293 and PR #13301.

### Metrics expiry test relies on wall-clock sleep and polling

- Category: timing/eventual consistency
- Evidence:
  - `/home/openclaw/coder/coderd/prometheusmetrics/aggregator_test.go:260` configures `MetricsExpiry: time.Millisecond`.
  - `/home/openclaw/coder/coderd/prometheusmetrics/aggregator_test.go:267` marks `TestUpdateMetrics_MetricsExpire` parallel.
  - `/home/openclaw/coder/coderd/prometheusmetrics/aggregator_test.go:295` sleeps for `10 * time.Millisecond` to cross the expiry boundary.
  - `/home/openclaw/coder/coderd/prometheusmetrics/aggregator_test.go:306` uses `require.Eventually(..., testutil.WaitShort, testutil.IntervalFast)` to wait for expired metrics to disappear.
- Why it can flake:
  - A 1ms expiry plus a 10ms sleep assumes wall-clock and scheduler behavior. Under CI load, goroutine scheduling and metric collection can delay either the update or the observation, making the result depend on timing rather than a controlled clock.
  - Parallel execution increases contention with other tests in the package.
- Proposed fix:
  - Inject a fake clock or expiry clock source into the aggregator so the test can advance time deterministically.
  - If fake clock injection is too invasive, widen the expiry threshold and make the polling assertion wait on an explicit aggregator update signal rather than elapsed wall time alone.
- Validation:
  - `cd /home/openclaw/coder && go test ./coderd/prometheusmetrics -run TestUpdateMetrics_MetricsExpire -count=100 -race`
- Historical references:
  - `categories/timing-eventual-consistency.md`: sleep-based synchronization and `require.Eventually` masking async readiness races.
  - `notes/common-solutions.md`: prefer fake clocks, explicit readiness signals, and deterministic synchronization over wall-clock sleeps.

### Purge tests compare database timestamps for exact equality

- Category: database/transactions/migrations
- Evidence:
  - `/home/openclaw/coder/coderd/database/dbpurge/dbpurge_test.go:619` requires `createdAt.UTC()` to exactly equal `wb.CreatedAt.UTC()`.
  - `/home/openclaw/coder/coderd/database/dbpurge/dbpurge_test.go:642` requires `wb.CreatedAt.UTC()` to exactly equal `wa.CreatedAt.UTC()`.
  - `/home/openclaw/coder/coderd/database/dbpurge/dbpurge_test.go:580` to `/home/openclaw/coder/coderd/database/dbpurge/dbpurge_test.go:669` builds workspace/app rows and validates timestamps after DB writes and reads.
- Why it can flake:
  - Postgres timestamp round-trips can differ by precision, monotonic clock stripping, location normalization, or server-side defaults. Exact `time.Time` equality is brittle when the value crosses a DB boundary.
  - The test already normalizes to UTC, but exact equality can still fail if precision differs.
- Proposed fix:
  - Normalize both values to the database precision before comparison, or use `require.WithinDuration(t, expected, actual, allowedDelta)` with a very small delta appropriate for Postgres timestamp precision.
  - Prefer comparing a durable semantic property if exact creation time is not what the purge behavior actually depends on.
- Validation:
  - `cd /home/openclaw/coder && go test ./coderd/database/dbpurge -run 'Test.*Workspace.*App|Test.*Purge' -count=100`
- Historical references:
  - `categories/database-transactions-migrations.md`: DB timestamp precision and transaction round-trip assertions.
  - `notes/common-solutions.md`: compare DB-derived times with precision-aware helpers instead of raw exact equality.

### DB metrics transaction test asserts raw log text after mocked retry state

- Category: database/transactions/migrations
- Evidence:
  - `/home/openclaw/coder/coderd/database/dbmetrics/dbmetrics_test.go:79` builds `txOpts := database.DefaultTXOptions().WithID(id)`.
  - `/home/openclaw/coder/coderd/database/dbmetrics/dbmetrics_test.go:80` manually increments execution count with `database.IncrementExecutionCount(txOpts)`.
  - `/home/openclaw/coder/coderd/database/dbmetrics/dbmetrics_test.go:82` to `/home/openclaw/coder/coderd/database/dbmetrics/dbmetrics_test.go:84` runs a failing transaction.
  - `/home/openclaw/coder/coderd/database/dbmetrics/dbmetrics_test.go:103` to `/home/openclaw/coder/coderd/database/dbmetrics/dbmetrics_test.go:108` asserts raw human log output substrings.
- Why it can flake:
  - This is not a current high-confidence flake, but it is brittle. The test depends on human log formatting and synthetic transaction retry state instead of a structured observer. Logger formatting changes can break it without a behavior regression.
  - The risk is higher because this package tests transaction metrics, where retry counts and labels are behaviorally important.
- Proposed fix:
  - Keep metric assertions as the primary behavior check.
  - If log coverage is required, use a structured slog sink/test handler and assert fields rather than rendered text.
  - Alternatively, split the log-format assertion into a narrow formatter unit test and keep transaction behavior tests format-independent.
- Validation:
  - `cd /home/openclaw/coder && go test ./coderd/database/dbmetrics -run TestInTxMetrics -count=100`
- Historical references:
  - `categories/database-transactions-migrations.md`: transaction retry assertions and observability checks coupled to implementation details.
  - `notes/proposed-solutions.md`: prefer structured synchronization/observation over incidental output strings.

## Clean patterns / non-findings

- Nested `t.Run` plus `t.Parallel` instances in `/home/openclaw/coder/coderd/database/querier_test.go`, `/home/openclaw/coder/coderd/database/dbauthz/customroles_test.go`, `/home/openclaw/coder/coderd/database/dbpurge/dbpurge_test.go`, and `/home/openclaw/coder/coderd/database/migrations/migrate_test.go` were inspected. I did not make a finding solely for loop-variable capture. Current Go semantics make stale `tc := tc` advice inappropriate, and the task explicitly forbids that recommendation.
- `/home/openclaw/coder/coderd/database/tx_test.go` uses gomock ordering for retry behavior and does not touch a real database. I did not find an actionable nondeterministic DB flake there.
- `/home/openclaw/coder/coderd/database/dbtestutil/postgres_test.go:115` to `/home/openclaw/coder/coderd/database/dbtestutil/postgres_test.go:122` contains a skipped manual timeout/leak test. Because it is skipped and explicitly manual, I did not count the `time.Sleep(11 * time.Minute)` as an actionable CI flake.
- `/home/openclaw/coder/coderd/database/migrations/migrate_test.go:370` to `/home/openclaw/coder/coderd/database/migrations/migrate_test.go:443` uses `testutil.WaitSuperLong` for a heavy migration test. It is expensive, but I did not find a specific shared-row, cleanup, or ordering hazard from the inspected lines.

## Next steps

1. Fix the pubsub goroutine assertions first. They are the clearest correctness issue and match prior pubsub flake history.
2. Convert the metrics expiry test to fake-clock or explicit-signal synchronization before widening timeouts.
3. Add a small DB time comparison helper for tests that validate timestamps across Postgres round-trips.
4. Re-run the targeted validation commands above with `-count=100` and `-race` where applicable before turning potential flakes into confirmed bugs.
