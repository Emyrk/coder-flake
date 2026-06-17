#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "categories"
OUT.mkdir(exist_ok=True)

CATEGORY_INFO = {
    "networking/proxy/websocket": {
        "slug": "networking-proxy-websocket",
        "title": "Networking, proxy, websocket",
        "summary": "Transport tests often assume the route, socket, proxy, websocket, DERP path, or tunnel is ready before it is. This is the largest bucket.",
        "why": "These failures are noisy because the test is observing a distributed system. A rerun can pass without proving the route or close path is deterministic.",
        "fixes": [
            "Add explicit server-ready signals before clients connect.",
            "Assert the selected route when a test cares about DERP, direct, proxy, or tunnel behavior.",
            "Use local fakes and injected transports instead of real DNS, tunnels, or outside services when product semantics allow it.",
            "Drain websocket readers and record close reasons before teardown.",
            "Use dynamic ports and listener-owned addresses. Do not hardcode ports.",
        ],
        "pilot": "Start with helper functions for server-ready, route-selected, message-ack, and close-drain states in high-flake network packages.",
    },
    "workspace/agent lifecycle": {
        "slug": "workspace-agent-lifecycle",
        "title": "Workspace, agent, provisioner lifecycle",
        "summary": "Tests assert before workspace builds, provisioner jobs, agents, PTYs, log streams, template versions, or app routes reach the expected state.",
        "why": "This bucket is core to Coder. It also overlaps with timing, DB-backed lifecycle, and resource flakes, so helper work here pays down several categories at once.",
        "fixes": [
            "Wait for exact lifecycle states: build created, provisioner job started, job complete, logs drained, agent ready, app route available.",
            "Make timeout errors print the last observed state.",
            "Use shared helpers instead of ad hoc polling in individual tests.",
            "Join background goroutines before cleanup cancels contexts.",
            "Add failure logs around provisioner and agent state transitions.",
        ],
        "pilot": "This is the best first implementation slice: build lifecycle helpers and migrate 3 to 5 existing flaky tests onto them.",
    },
    "concurrency/race": {
        "slug": "concurrency-race",
        "title": "Concurrency and races",
        "summary": "Shared mutable state, goroutines, waitgroups, contexts, maps, and parallel subtests produce nondeterministic outcomes.",
        "why": "Race flakes are often real product bugs or test harness bugs that only show up under unlucky scheduling. Reruns hide them until they come back worse.",
        "fixes": [
            "Scope mutable state per subtest. Do not share maps, buffers, contexts, or handles across parallel subtests without synchronization.",
            "Use per-subtest contexts so one timeout does not poison sibling subtests.",
            "Join goroutines before cleanup and context cancellation.",
            "Never call `t.Fatal`, `require.*`, or `assert.*` from non-test goroutines.",
            "Verify race suspects with `go test -race -count=N`.",
        ],
        "pilot": "Add review checks and helper patterns for goroutine joins, per-subtest contexts, and synchronized shared state.",
    },
    "database/transactions/migrations": {
        "slug": "database-transactions-migrations",
        "title": "Database, transactions, migrations",
        "summary": "DB-backed tests fail around shared Postgres resources, cleanup gaps, socket leaks, transaction timing, migrations, and DB-backed async state.",
        "why": "Postgres amplifies timing and isolation mistakes. The failure often looks like a product assertion, but the cause is shared test infrastructure.",
        "fixes": [
            "Create isolated DB resources per test where practical.",
            "Clean up one-shot DBs, sockets, listeners, and rows explicitly.",
            "Use direct DB setup only when API-level setup introduces unrelated async races.",
            "Cap DB-heavy package parallelism separately from pure unit tests.",
            "Avoid exact timestamp equality after database round trips.",
        ],
        "pilot": "Inventory DB-heavy flaky packages and split their parallelism profile from cheap unit tests.",
    },
    "browser/e2e/playwright": {
        "slug": "browser-e2e-playwright",
        "title": "Browser, e2e, Playwright",
        "summary": "UI tests assert against transient state, ambiguous selectors, unflushed React state, missing browser dependencies, or navigation before the page settles.",
        "why": "Frontend flakes are expensive to debug after the fact. Without traces and locator state, the useful evidence is usually gone.",
        "fixes": [
            "Use stable selectors and avoid broad text or role matches that can hit multiple elements.",
            "Wait for settled UI state, not transient URLs or immediate DOM shape.",
            "Upload Playwright traces, screenshots, videos, URL, and locator state on failure.",
            "Repeat affected specs in a targeted workflow instead of rerunning the whole suite blindly.",
            "Make browser dependencies explicit in CI images or setup.",
        ],
        "pilot": "Require trace artifacts for browser flake detection and migrate the noisiest specs to stable locator helpers.",
    },
    "timing/eventual consistency": {
        "slug": "timing-eventual-consistency",
        "title": "Timing and eventual consistency",
        "summary": "Tests check async state before convergence or compare wall-clock values too tightly.",
        "why": "This category is where bigger timeouts are most tempting. Sometimes they help, but they often hide missing synchronization.",
        "fixes": [
            "Inject clocks or pass explicit time values in scheduling, TTL, metrics, and status tests.",
            "Poll for the actual condition and print the last observed state on timeout.",
            "Avoid multiple `time.Now()` calls around boundary assertions.",
            "Widen time ranges only when the product genuinely measures wall-clock elapsed time.",
            "Use deterministic fixtures for timezone and precision boundaries.",
        ],
        "pilot": "Add deterministic clock guidance and search for exact boundary assertions around scheduling and metrics tests.",
    },
    "platform/os-specific CI behavior": {
        "slug": "platform-os-specific-ci-behavior",
        "title": "Platform or OS-specific CI behavior",
        "summary": "Failures depend on Windows, macOS, ARM64, shell behavior, hosted runner speed, browser availability, or Postgres behavior on a platform.",
        "why": "Platform flakes often get dismissed as CI weirdness. They still define the contract our test suite is making with CI.",
        "fixes": [
            "Record OS, CPU, memory, shell, and package parallelism in failure output.",
            "Use platform helpers where behavior legitimately differs.",
            "Lower parallelism for platform-sensitive jobs instead of slowing every job.",
            "Skip only with owner, issue link, category, date, and retirement condition.",
            "Make browser and system dependencies explicit for each platform.",
        ],
        "pilot": "Add runner metadata to high-risk jobs and split platform-sensitive packages into their own parallelism profile.",
    },
    "resource exhaustion/timeout": {
        "slug": "resource-exhaustion-timeout",
        "title": "Resource exhaustion and timeouts",
        "summary": "Slow runners, CPU pressure, memory pressure, PTY exhaustion, OOMs, and overloaded parallel jobs show up as nondeterministic timeouts.",
        "why": "A timeout is a symptom, not a root cause. Without runner and package fanout data, teams usually guess.",
        "fixes": [
            "Log runner CPU, memory, job name, package, and parallelism in failure output.",
            "Cap Postgres, PTY, browser, and network-heavy packages separately from cheap tests.",
            "Avoid blanket timeout increases unless the product actually depends on wall-clock elapsed time.",
            "Separate resource-sensitive stress runs from normal PR checks.",
            "Track rerun minutes consumed by known flaky signatures.",
        ],
        "pilot": "Measure package fanout for the highest timeout buckets and tune parallelism by package class.",
    },
    "test isolation/order dependency": {
        "slug": "test-isolation-order-dependency",
        "title": "Test isolation and order dependency",
        "summary": "Tests leak state through temp dirs, caches, duplicate names, reused ports, contexts, cleanup gaps, random order, or parallel subtests.",
        "why": "These failures are preventable. The suite should not depend on test order or shared global state unless the test says so explicitly.",
        "fixes": [
            "Generate unique users, orgs, workspace names, ports, paths, and DB rows per test.",
            "Avoid shared mutable testcase structs in parallel subtests.",
            "Use temp dirs and cleanup checks that wait for background work to finish.",
            "Randomize test order in detection workflows to expose hidden coupling.",
            "Document helpers for unique names and isolated test resources.",
        ],
        "pilot": "Add reusable unique-resource helpers and run randomized order checks on known-isolation packages.",
    },
    "external service/dependency": {
        "slug": "external-service-dependency",
        "title": "External service and dependency",
        "summary": "Some flakes depend on outside services or dependency managers: OpenAI, DNS, Docker setup, registries, CDNs, browser downloads, or auth providers.",
        "why": "External systems create noise unless the test explicitly exists to validate that external integration.",
        "fixes": [
            "Use fake servers or injected transports for CI tests.",
            "Keep true external round trips out of normal PR checks.",
            "Pin and provision browser/system dependencies explicitly.",
            "Quarantine unavoidable external tests behind owner and expiry metadata.",
            "Record dependency versions and upstream error details in failure output.",
        ],
        "pilot": "List tests with real external dependencies and move them behind fakes, targeted jobs, or explicit quarantine.",
    },
    "unknown/needs manual read": {
        "slug": "unknown-needs-manual-read",
        "title": "Unknown or needs manual read",
        "summary": "The downloaded metadata did not contain enough detail to classify the failure with confidence.",
        "why": "Unknown is a signal that failure artifacts are too thin. It should shrink as intake and artifact capture improve.",
        "fixes": [
            "Improve flake issue templates so reports include test name, package, job, platform, error signature, and rerun status.",
            "Upload logs, traces, screenshots, and last observed state for high-risk areas.",
            "Track unknowns separately instead of forcing fake precision.",
            "Manually read the highest-impact unknowns and reclassify them.",
        ],
        "pilot": "Manually classify the top unknowns and use the gaps to improve the intake template.",
    },
    "not-a-test-flake/nix-flake-or-maintenance": {
        "slug": "not-a-test-flake-nix-flake-or-maintenance",
        "title": "Not a test flake: Nix flake or maintenance",
        "summary": "These references matched the word flake, but they are about `flake.nix`, `flake.lock`, update-flake automation, or dependency maintenance.",
        "why": "Keep these out of nondeterministic test-flake metrics. They are useful CI maintenance signals, but they answer a different question.",
        "fixes": [
            "Filter them out of test-flake dashboards.",
            "Track Nix maintenance separately if needed.",
            "Use the category as a false-positive bucket for search hygiene.",
        ],
        "pilot": "Exclude this category from test-flake incident counts and keep it only as a search-quality note.",
    },
}

ORDER = [
    "networking/proxy/websocket",
    "workspace/agent lifecycle",
    "concurrency/race",
    "database/transactions/migrations",
    "browser/e2e/playwright",
    "timing/eventual consistency",
    "platform/os-specific CI behavior",
    "resource exhaustion/timeout",
    "test isolation/order dependency",
    "external service/dependency",
    "unknown/needs manual read",
    "not-a-test-flake/nix-flake-or-maintenance",
]

CODE_EXAMPLES = {
    "networking/proxy/websocket": [
        ("Bad: connect before the server is ready", """```go
go srv.Serve(listener)

conn, _, err := websocket.DefaultDialer.Dial(url, nil)
require.NoError(t, err)
```"""),
        ("Better: publish a readiness signal, then connect", """```go
ready := make(chan struct{})
srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
	select {
	case <-ready:
	default:
		close(ready)
	}
	serveWebsocket(w, r)
}))
t.Cleanup(srv.Close)

require.Eventually(t, func() bool {
	resp, err := srv.Client().Get(srv.URL + "/healthz")
	if err != nil {
		return false
	}
	_ = resp.Body.Close()
	return resp.StatusCode == http.StatusOK
}, testutil.WaitLong, testutil.IntervalFast)

<-ready
conn, _, err := websocket.DefaultDialer.Dial(wsURL(srv.URL), nil)
require.NoError(t, err)
```"""),
    ],
    "workspace/agent lifecycle": [
        ("Bad: assert immediately after creating async work", """```go
build := coderdtest.CreateWorkspaceBuild(t, client, workspace.ID)

agent, err := client.WorkspaceAgent(ctx, build.Resources[0].Agents[0].ID)
require.NoError(t, err)
require.Equal(t, codersdk.WorkspaceAgentConnected, agent.Status)
```"""),
        ("Better: wait for the exact lifecycle state and print the last state", """```go
build := coderdtest.CreateWorkspaceBuild(t, client, workspace.ID)

var last codersdk.WorkspaceAgent
require.Eventuallyf(t, func() bool {
	agent, err := client.WorkspaceAgent(ctx, build.Resources[0].Agents[0].ID)
	if err != nil {
		return false
	}
	last = agent
	return agent.Status == codersdk.WorkspaceAgentConnected
}, testutil.WaitLong, testutil.IntervalFast, "last agent state: %+v", last)
```"""),
    ],
    "concurrency/race": [
        ("Bad: assert from a background goroutine", """```go
go func() {
	result, err := doAsyncWork(ctx)
	require.NoError(t, err)
	require.Equal(t, want, result)
}()
```"""),
        ("Better: send results back to the test goroutine", """```go
type result struct {
	value string
	err   error
}
results := make(chan result, 1)

go func() {
	value, err := doAsyncWork(ctx)
	results <- result{value: value, err: err}
}()

select {
case got := <-results:
	require.NoError(t, got.err)
	require.Equal(t, want, got.value)
case <-time.After(testutil.WaitLong):
	t.Fatal("timed out waiting for async work")
}
```"""),
    ],
    "database/transactions/migrations": [
        ("Bad: share mutable DB rows across parallel tests", """```go
user := dbgen.User(t, db, database.User{})

t.Run("first", func(t *testing.T) {
	t.Parallel()
	require.NoError(t, db.UpdateUser(ctx, user.ID, patchA))
})
t.Run("second", func(t *testing.T) {
	t.Parallel()
	require.NoError(t, db.UpdateUser(ctx, user.ID, patchB))
})
```"""),
        ("Better: create isolated DB resources per subtest", """```go
for _, tc := range cases {
	t.Run(tc.name, func(t *testing.T) {
		t.Parallel()
		user := dbgen.User(t, db, database.User{
			Email: testutil.GetRandomName(t) + "@example.com",
		})
		require.NoError(t, db.UpdateUser(ctx, user.ID, tc.patch))
	})
}
```"""),
    ],
    "browser/e2e/playwright": [
        ("Bad: assert against broad text while the UI is still changing", """```ts
await page.goto(`/workspaces/${workspaceName}`);
await expect(page.getByText("Running")).toBeVisible();
```"""),
        ("Better: use stable locators and wait for the settled state", """```ts
await page.goto(`/workspaces/${workspaceName}`);

const status = page.getByTestId("workspace-status");
await expect(status).toHaveText("Running", { timeout: 30_000 });

await test.info().attach("workspace-url", {
	body: page.url(),
	contentType: "text/plain",
});
```"""),
    ],
    "timing/eventual consistency": [
        ("Bad: sleep and hope the async state converged", """```go
triggerReconciliation(ctx)
time.Sleep(2 * time.Second)

got, err := store.GetStatus(ctx, id)
require.NoError(t, err)
require.Equal(t, StatusReady, got)
```"""),
        ("Better: poll the condition and report the last observed value", """```go
triggerReconciliation(ctx)

var last Status
require.Eventuallyf(t, func() bool {
	got, err := store.GetStatus(ctx, id)
	if err != nil {
		return false
	}
	last = got
	return got == StatusReady
}, testutil.WaitLong, testutil.IntervalFast, "last status: %s", last)
```"""),
    ],
    "platform/os-specific CI behavior": [
        ("Bad: assume Linux shell and paths everywhere", """```go
cmd := exec.Command("sh", "-c", "touch /tmp/coder-test-file")
require.NoError(t, cmd.Run())
```"""),
        ("Better: use Go APIs or isolate platform-specific behavior", """```go
dir := t.TempDir()
path := filepath.Join(dir, "coder-test-file")

require.NoError(t, os.WriteFile(path, []byte("ok"), 0o600))
_, err := os.Stat(path)
require.NoError(t, err)
```"""),
    ],
    "resource exhaustion/timeout": [
        ("Bad: unbounded parallel work inside an already parallel package", """```go
for _, workspace := range workspaces {
	go func() {
		_ = startWorkspace(ctx, workspace)
	}()
}
```"""),
        ("Better: bound fanout and join before cleanup", """```go
group, ctx := errgroup.WithContext(ctx)
group.SetLimit(4)

for _, workspace := range workspaces {
	group.Go(func() error {
		return startWorkspace(ctx, workspace)
	})
}

require.NoError(t, group.Wait())
```"""),
    ],
    "test isolation/order dependency": [
        ("Bad: reuse global names, ports, or paths", """```go
const workspaceName = "test-workspace"

workspace := dbgen.Workspace(t, db, database.Workspace{
	Name: workspaceName,
})
```"""),
        ("Better: generate unique resources per test", """```go
workspaceName := testutil.GetRandomName(t)

workspace := dbgen.Workspace(t, db, database.Workspace{
	Name: workspaceName,
})
t.Cleanup(func() {
	_ = db.DeleteWorkspace(context.Background(), workspace.ID)
})
```"""),
    ],
    "external service/dependency": [
        ("Bad: call the real external service from PR CI", """```go
client := openai.NewClient(os.Getenv("OPENAI_API_KEY"))
resp, err := client.CreateChatCompletion(ctx, req)
require.NoError(t, err)
require.NotEmpty(t, resp.Choices)
```"""),
        ("Better: inject a fake transport with deterministic responses", """```go
server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
	require.Equal(t, "/v1/chat/completions", r.URL.Path)
	w.Header().Set("Content-Type", "application/json")
	_, _ = w.Write([]byte(`{"choices":[{"message":{"content":"ok"}}]}`))
}))
t.Cleanup(server.Close)

client := openai.NewClientForTest(server.URL, server.Client())
resp, err := client.CreateChatCompletion(ctx, req)
require.NoError(t, err)
require.Equal(t, "ok", resp.Choices[0].Message.Content)
```"""),
    ],
    "unknown/needs manual read": [
        ("Bad: file an unclassifiable flake report", """```md
Test failed again. Rerun passed.
```"""),
        ("Better: capture a minimum useful flake signature", """```md
## Flake signature
- Test: TestWorkspaceAgentReconnect
- Package: coderd/workspaces
- Job: linux-amd64-postgres
- Platform: ubuntu-24.04, 4 CPU
- Error: timed out waiting for agent status connected
- Rerun: passed on attempt 2
- Artifacts: logs, trace, last observed agent state
```"""),
    ],
    "not-a-test-flake/nix-flake-or-maintenance": [
        ("Bad: mix Nix maintenance with test-flake counts", """```sql
select count(*)
from github_references
where lower(title) like '%flake%';
```"""),
        ("Better: filter false positives before reporting test flakes", """```sql
select count(*)
from github_references
where category != 'not-a-test-flake/nix-flake-or-maintenance';
```"""),
    ],
}


ADDITIONAL_CODE_EXAMPLES = {
    "networking/proxy/websocket": [
        ("Bad: ignore websocket close reasons", """```go
_ = conn.Close()
require.NoError(t, <-readerDone)
```"""),
        ("Better: drain the reader and assert the expected close", """```go
closeErr := make(chan error, 1)
go func() {
	for {
		_, _, err := conn.ReadMessage()
		if err != nil {
			closeErr <- err
			return
		}
	}
}()

require.NoError(t, conn.WriteControl(
	websocket.CloseMessage,
	websocket.FormatCloseMessage(websocket.CloseNormalClosure, "done"),
	time.Now().Add(time.Second),
))
require.Eventually(t, func() bool {
	select {
	case err := <-closeErr:
		return websocket.IsCloseError(err, websocket.CloseNormalClosure)
	default:
		return false
	}
}, testutil.WaitShort, testutil.IntervalFast)
```"""),
    ],
    "workspace/agent lifecycle": [
        ("Bad: cancel the context before logs drain", """```go
ctx, cancel := context.WithCancel(context.Background())
logs := agent.StartupLogs(ctx)

cancel()
require.Contains(t, logs.String(), "agent started")
```"""),
        ("Better: wait for the log marker, then clean up", """```go
ctx, cancel := context.WithCancel(context.Background())
t.Cleanup(cancel)
logs := agent.StartupLogs(ctx)

require.Eventually(t, func() bool {
	return strings.Contains(logs.String(), "agent started")
}, testutil.WaitLong, testutil.IntervalFast)
```"""),
    ],
    "concurrency/race": [
        ("Bad: share mutable state across parallel subtests", """```go
seen := map[string]bool{}
for _, name := range names {
	t.Run(name, func(t *testing.T) {
		t.Parallel()
		seen[name] = true
	})
}
```"""),
        ("Better: keep parallel subtest state local or synchronized", """```go
var mu sync.Mutex
seen := map[string]bool{}
for _, name := range names {
	t.Run(name, func(t *testing.T) {
		t.Parallel()
		mu.Lock()
		defer mu.Unlock()
		seen[name] = true
	})
}
```"""),
    ],
    "database/transactions/migrations": [
        ("Bad: assert exact timestamps after a DB round trip", """```go
now := time.Now()
row := dbgen.Token(t, db, database.Token{CreatedAt: now})

require.Equal(t, now, row.CreatedAt)
```"""),
        ("Better: compare within precision the DB actually preserves", """```go
now := dbtime.Now()
row := dbgen.Token(t, db, database.Token{CreatedAt: now})

require.WithinDuration(t, now, row.CreatedAt, time.Millisecond)
```"""),
    ],
    "browser/e2e/playwright": [
        ("Bad: click before the async request settles", """```ts
await page.getByRole("button", { name: "Save" }).click();
await expect(page.getByText("Saved")).toBeVisible();
```"""),
        ("Better: wait for the API response and final UI state", """```ts
await Promise.all([
	page.waitForResponse((res) =>
		res.url().includes("/api/v2/workspaces") && res.status() === 200,
	),
	page.getByRole("button", { name: "Save" }).click(),
]);
await expect(page.getByTestId("save-status")).toHaveText("Saved");
```"""),
    ],
    "timing/eventual consistency": [
        ("Bad: compare against a second `time.Now()` at the boundary", """```go
expiresAt := time.Now().Add(time.Hour)
require.True(t, expiresAt.After(time.Now().Add(59*time.Minute)))
```"""),
        ("Better: inject one clock value and derive expectations from it", """```go
clock := quartz.NewMock(t)
now := clock.Now()
expiresAt := now.Add(time.Hour)

require.Equal(t, now.Add(time.Hour), expiresAt)
```"""),
    ],
    "platform/os-specific CI behavior": [
        ("Bad: assume a fixed shell binary", """```go
cmd := exec.Command("bash", "-lc", "echo ok")
require.NoError(t, cmd.Run())
```"""),
        ("Better: skip or branch with explicit platform intent", """```go
if runtime.GOOS == "windows" {
	t.Skip("tracked in #12345: requires POSIX shell semantics")
}
cmd := exec.Command("bash", "-lc", "echo ok")
require.NoError(t, cmd.Run())
```"""),
    ],
    "resource exhaustion/timeout": [
        ("Bad: timeout without runner context", """```go
ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
defer cancel()

require.NoError(t, runLargeScenario(ctx))
```"""),
        ("Better: include package fanout and runner context in timeout failures", """```go
ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
defer cancel()

err := runLargeScenario(ctx)
require.NoErrorf(t, err, "job=%s package=%s parallel=%d cpus=%d",
	os.Getenv("GITHUB_JOB"), "coderd", runtime.GOMAXPROCS(0), runtime.NumCPU(),
)
```"""),
    ],
    "test isolation/order dependency": [
        ("Bad: bind to a hardcoded port", """```go
ln, err := net.Listen("tcp", "127.0.0.1:3000")
require.NoError(t, err)
```"""),
        ("Better: let the listener allocate the port", """```go
ln, err := net.Listen("tcp", "127.0.0.1:0")
require.NoError(t, err)
t.Cleanup(func() { _ = ln.Close() })

addr := ln.Addr().String()
```"""),
    ],
    "external service/dependency": [
        ("Bad: depend on DNS or the internet for product-neutral behavior", """```go
resp, err := http.Get("https://example.com/healthz")
require.NoError(t, err)
require.Equal(t, http.StatusOK, resp.StatusCode)
```"""),
        ("Better: use an `httptest.Server` for product-neutral behavior", """```go
srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
}))
t.Cleanup(srv.Close)

resp, err := srv.Client().Get(srv.URL + "/healthz")
require.NoError(t, err)
require.Equal(t, http.StatusOK, resp.StatusCode)
```"""),
    ],
    "unknown/needs manual read": [
        ("Bad: omit reproduction scope", """```md
Saw a flake in CI. Not sure what happened.
```"""),
        ("Better: include the targeted rerun command", """```md
## Reproduction
- Command: `go test ./coderd -run TestWorkspaceAgentReconnect -count=50`
- Result: failed 2/50 on linux-amd64-postgres
- First failing seed/log: <artifact URL>
```"""),
    ],
    "not-a-test-flake/nix-flake-or-maintenance": [
        ("Bad: tag every `flake.lock` update as CI flake work", """```md
Labels: flake, ci, reliability
Title: chore: update flake.lock
```"""),
        ("Better: route Nix maintenance separately", """```md
Labels: nix, dependencies
Title: chore: update flake.lock

Not counted in nondeterministic test-flake metrics.
```"""),
    ],
}


def clean(s: str, n: int = 360) -> str:
    s = re.sub(r"\s+", " ", s or "").strip()
    s = (
        s.replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2019", "'")
        .replace("\u2026", "...")
    )
    s = s.replace("|", "\\|")
    if len(s) > n:
        return s[: n - 3].rstrip() + "..."
    return s


def gh_link(kind: str, number: str) -> str:
    if kind == "PR":
        return f"[PR #{number}](https://github.com/coder/coder/pull/{number})"
    return f"[issue #{number}](https://github.com/coder/coder/issues/{number})"


def load_pr_attribution() -> dict[str, dict[str, str]]:
    attribution: dict[str, dict[str, str]] = {}
    for pull_path in (ROOT / "raw/prs").glob("*/pull.json"):
        data = json.loads(pull_path.read_text(encoding="utf-8"))
        number = str(data.get("number") or pull_path.parent.name)
        user = data.get("user") or {}
        merged_by = data.get("merged_by") or {}
        attribution[number] = {
            "author": user.get("login") or "",
            "merged_by": merged_by.get("login") or "",
            "merged": "yes" if data.get("merged") else "no",
        }
    return attribution


def user_link(login: str) -> str:
    if not login:
        return ""
    return f"[@{login}](https://github.com/{login})"


def solved_by(r: dict[str, str], pr_attribution: dict[str, dict[str, str]]) -> str:
    if r["kind"] == "PR":
        pr = pr_attribution.get(r["number"], {})
        if pr.get("merged") == "yes":
            return user_link(pr.get("author", ""))
        return ""

    solved: list[str] = []
    for number in re.findall(r"#(\d+)", r.get("linked_fix_prs", "")):
        pr = pr_attribution.get(number, {})
        if pr.get("merged") == "yes":
            author = user_link(pr.get("author", ""))
            if author and author not in solved:
                solved.append(author)
    return ", ".join(solved)


def ref_table(rows: list[dict[str, str]], pr_attribution: dict[str, dict[str, str]]) -> str:
    lines = ["| ref | type | title | status | solved by | evidence |", "| --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        lines.append(
            f"| {gh_link(r['kind'], r['number'])} | {r['kind']} | {clean(r['title'], 120)} | {clean(r['status'], 80)} | {solved_by(r, pr_attribution)} | {clean(r['evidence'], 320)} |"
        )
    return "\n".join(lines)


def code_examples(category: str) -> str:
    examples = CODE_EXAMPLES[category] + ADDITIONAL_CODE_EXAMPLES.get(category, [])
    lines = ["<details>", "<summary>Code examples</summary>", ""]
    for title, snippet in examples:
        lines += [f"### {title}", "", snippet, ""]
    lines += ["</details>"]
    return "\n".join(lines)


def category_page(category: str, rows: list[dict[str, str]], pr_attribution: dict[str, dict[str, str]]) -> str:
    info = CATEGORY_INFO[category]
    counts = Counter(r["kind"] for r in rows)
    fixes = "\n".join(f"- {x}" for x in info["fixes"])
    examples = code_examples(category)
    return f"""# {info['title']}

{info['summary']}

## Count

| references | issues | PRs |
| ---: | ---: | ---: |
| {len(rows)} | {counts.get('issue', 0)} | {counts.get('PR', 0)} |

## Why it flakes

{info['why']}

## Common fixes

{fixes}

## Code examples

These examples are illustrative patterns for the category, not direct patches against one specific test.

{examples}

## Suggested first slice

{info['pilot']}

<details>
<summary>References ({len(rows)})</summary>

`solved by` is the author of the merged PR, either the reference itself or a linked fix PR. It is blank when the corpus did not identify a merged fix PR.

{ref_table(rows, pr_attribution)}

</details>
"""


def one_pager(category_rows: dict[str, list[dict[str, str]]]) -> str:
    total = sum(len(v) for v in category_rows.values())
    lines = [
        "# Coder CI flakes: wiki summary",
        "",
        "A flake is a test or CI failure that fails nondeterministically, then often passes on rerun. We analyzed flake-related issues and PRs in [`coder/coder`](https://github.com/coder/coder), grouped them by failure mode, and looked for fixes that repeat.",
        "",
        "## What we found",
        "",
        "Coder flakes are not random. Most fall into a few recurring buckets.",
        "",
        "| rank | category | references | common fix |",
        "| ---: | --- | ---: | --- |",
    ]
    ranked = sorted([c for c in ORDER if c in category_rows], key=lambda c: len(category_rows[c]), reverse=True)
    for i, cat in enumerate(ranked, 1):
        info = CATEGORY_INFO[cat]
        lines.append(f"| {i} | [{info['title']}](categories/{info['slug']}.md) | {len(category_rows[cat])} | {info['fixes'][0]} |")
    lines += [
        "",
        f"References means GitHub artifacts in the research corpus: one issue or one PR. This corpus has {total} references total. It is not a count of unique flaky tests.",
        "",
        "## Quick and dirty",
        "",
        "The repeated mistakes, sorted roughly by occurrence:",
        "",
        "- Network tests assume the route, socket, websocket, DERP path, or proxy state is ready before it is.",
        "- Workspace and agent tests assert before provisioners, agents, builds, PTYs, logs, or apps reach the expected lifecycle point.",
        "- Parallel tests share state: maps, contexts, transports, users, deployments, ports, DB rows, or goroutines.",
        "- DB-backed tests leak resources or depend on timing around transactions, migrations, cleanup, or Postgres runner behavior.",
        "- Browser tests assert against transient UI state, ambiguous selectors, or navigation before the page settles.",
        "- Time-based tests compare wall-clock values too tightly or call `time.Now()` around boundaries.",
        "- CI jobs run platform-sensitive tests with the wrong assumptions about OS, CPU, memory, shell, browser, or Postgres behavior.",
        "- Quarantine sometimes removes pain without recording owner, expiry, or retirement criteria.",
        "",
        "## Recommended approach",
        "",
        "Do not solve this as one giant flake cleanup. Treat it as a reliability program with category-specific fixes.",
        "",
        "1. Track flakes by signature: test name, package, normalized error, category, job, platform, linked issue or PR.",
        "2. Add an intake template with failure link, category, suspected owner, reproduction command, rerun status, first seen, and last seen.",
        "3. Fix top buckets with shared helpers: networking readiness, lifecycle waits, concurrency isolation, DB resource isolation, browser trace artifacts, deterministic time.",
        "4. Quarantine with discipline: issue link, owner, category, date, retirement condition, and default expiry.",
        "5. Add targeted detection: `go test -count=N`, `-race` for race suspects, nightly stress for high-risk packages, and repeated browser specs with traces.",
        "",
        "## First workstream to pilot",
        "",
        "Pick one category and make it boring.",
        "",
        "Best pilot: [workspace, agent, and provisioner lifecycle](categories/workspace-agent-lifecycle.md). It is the second largest bucket, core to Coder, and the helper work should reduce timing, DB-backed lifecycle, and resource flakes too.",
        "",
        "This is not the only category. It is just the best first slice.",
        "",
        "## Links",
        "",
        "- [Full proposal](notes/proposed-solutions.md)",
        "- [Common fixes by category](notes/common-solutions.md)",
        "- [Category taxonomy](notes/category-taxonomy.md)",
        "- [Categorized data](processed/categories.csv)",
        "- [Raw data and crawler](README.md)",
        "",
        "<details>",
        "<summary>Dataset details</summary>",
        "",
        "Seed search:",
        "",
        "- `repo:coder/coder type:issue flake in:title`",
        "- `repo:coder/coder type:issue flaky in:title`",
        "- `repo:coder/coder type:pr flake in:title`",
        "- `repo:coder/coder type:pr flaky in:title`",
        "",
        "Expanded corpus:",
        "",
        "- 219 seed flake issues enriched",
        "- 344 candidate PRs enriched",
        "- 11 PRs discovered beyond title matches via issue timeline cross references",
        "- 14 timeline cross references",
        "- 26 PR body references to seed issues",
        "- 563 categorized references total",
        "",
        "This is a flake candidate corpus, not every issue and PR in `coder/coder`.",
        "",
        "</details>",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    with (ROOT / "processed/categories.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    by_cat: dict[str, list[dict[str, str]]] = {}
    for r in rows:
        by_cat.setdefault(r["category"], []).append(r)
    pr_attribution = load_pr_attribution()
    for cat, cat_rows in by_cat.items():
        info = CATEGORY_INFO[cat]
        (OUT / f"{info['slug']}.md").write_text(category_page(cat, cat_rows, pr_attribution), encoding="utf-8")
    (ROOT / "ONE_PAGER.md").write_text(one_pager(by_cat), encoding="utf-8")


if __name__ == "__main__":
    main()
