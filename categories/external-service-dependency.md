# External service and dependency

Some flakes depend on outside services or dependency managers: OpenAI, DNS, Docker setup, registries, CDNs, browser downloads, or auth providers.

## Count

| references | issues | PRs |
| ---: | ---: | ---: |
| 4 | 2 | 2 |

## Why it flakes

External systems create noise unless the test explicitly exists to validate that external integration.

## Common fixes

- Use fake servers or injected transports for CI tests.
- Keep true external round trips out of normal PR checks.
- Pin and provision browser/system dependencies explicitly.
- Quarantine unavoidable external tests behind owner and expiry metadata.
- Record dependency versions and upstream error details in failure output.

## Code examples

These examples are illustrative patterns for the category, not direct patches against one specific test.

<details>
<summary>Code examples</summary>

### Bad: call the real external service from PR CI

```go
client := openai.NewClient(os.Getenv("OPENAI_API_KEY"))
resp, err := client.CreateChatCompletion(ctx, req)
require.NoError(t, err)
require.NotEmpty(t, resp.Choices)
```

### Better: inject a fake transport with deterministic responses

```go
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
```

</details>

## Suggested first slice

List tests with real external dependencies and move them behind fakes, targeted jobs, or explicit quarantine.

<details>
<summary>References (4)</summary>

`solved by` is the author of the merged PR, either the reference itself or a linked fix PR. It is blank when the corpus did not identify a merged fix PR.

| ref | type | title | status | solved by | evidence |
| --- | --- | --- | --- | --- | --- |
| [issue #10105](https://github.com/coder/coder/issues/10105) | issue | flake: WorkspaceSchedulePage › autostop › uses template default ttl when first enabled | closed |  | ...\| FormLanguage.stopSwitch, 273 \| ); 274 \| // enable autostop at waitForWrapper (node_modules/.pnpm/@testing-library+dom@9.3.1/node_modules/@testing-library/dom/dist/wait-for.js:160:27) at node_modules/.pnpm/@testing-library+dom@9.3.1/node_modules/@testing-library/dom/dist/query-helpers.js:86:31 at Object.findB... |
| [issue #14535](https://github.com/coder/coder/issues/14535) | issue | flake: `UsersPage.test.tsx` | closed |  | ...moreButtons[0]; 28 \| await user.click(firstMoreButton); 29 \| at waitForWrapper (node_modules/.pnpm/@testi flake: `UsersPage.test.tsx` https://github.com/coder/coder/actions/runs/10680634527/job/29602816185 ``` FAIL src/pages/UsersPage/UsersPage.test.tsx (19.402 s) ● UsersPage › suspend user › when it is success... |
| [PR #23877](https://github.com/coder/coder/pull/23877) | PR | test(coderd/x/chatd): remove flaky OpenAI round-trip tests | closed; merged | [@ibetitsmike](https://github.com/ibetitsmike) | ...rom `coderd/x/chatd/integration_test.go` and drop the now-unused fake upstream capture code. Closes https://github.com/coder/internal/issues/1433 test(coderd/x/chatd): remove flaky OpenAI round-trip tests These OpenAI reasoning + web search round-trip integration tests keep flaking in CI even after the recent tim... |
| [PR #25015](https://github.com/coder/coder/pull/25015) | PR | fix(coderd/externalauth): isolate TestValidateToken transports to fix flake | closed; merged | [@zedkipp](https://github.com/zedkipp) | fix(coderd/externalauth): isolate TestValidateToken transports to fix flake This change uses separate http clients/transports in TestValidateToken subtests. Previously parallel subtests of TestValidateToken shared http.DefaultTransport. When one subtest's httptest.Server.Close() ran in t.Cleanup, it called http.Defa... |

</details>
