# Potential flake solution notes

This directory contains static audits of the current `github.com/coder/coder` checkout, using the Coder flake research corpus as the knowledge base.

These reports identify potential flakes. They are not confirmed bugs unless a report explicitly says it reproduced the failure. Treat each finding as a hypothesis backed by file and line evidence, then validate it with the command listed in the report.

## Reports

- [Summary](summary.md), cross-area synthesis and suggested repair order.
- [Networking, proxy, websocket](networking-proxy-websocket.md), network-heavy tests, tailnet, workspace proxy, websocket, and traffic scaletests.
- [Workspace, agent, provisioner lifecycle](workspace-agent-lifecycle.md), lifecycle waits, provisionerd reconnects, startup logs, boundary log proxy, and agent metadata timing.
- [Concurrency and resource timeouts](concurrency-resource-timeout.md), background goroutine assertions, fanout, sleeps, unjoined servers, and opaque timeouts.
- [Browser, e2e, Playwright](browser-e2e-playwright.md), frontend e2e waits, React Testing Library synchronization, shared names, and external OIDC discovery.
- [Database, transactions, pubsub, migrations](database-transactions-migrations.md), pubsub goroutines, DB-backed timing, metrics expiry, timestamp comparisons, and transaction log assertions.

## How to read these notes

Start with [Summary](summary.md) for the cross-cutting repair order. Then open the area report for the exact file and line evidence, proposed fix, validation command, and historical references.

Use the taxonomy names from the reports when filing follow-up work:

- `networking/proxy/websocket`
- `workspace/agent lifecycle`
- `concurrency/race`
- `database/transactions/migrations`
- `browser/e2e/playwright`
- `timing/eventual consistency`
- `platform/os-specific CI behavior`
- `resource exhaustion/timeout`
- `test isolation/order dependency`
- `external service/dependency`

Do not treat these notes as a bug list without validation. The strongest candidates are the patterns that appear in multiple reports: assertions from non-test goroutines, fixed sleeps as synchronization, lifecycle assertions before side effects settle, and resource-heavy fanout without local budgets.
