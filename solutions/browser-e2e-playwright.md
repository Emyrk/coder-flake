# Browser, e2e, frontend potential flakes

## Scope

Audited potential nondeterministic flakes in the current `github.com/coder/coder` checkout under `site/`, focused on Playwright e2e specs, React/Vitest/testing-library tests, frontend API mocking, browser dependency setup, and UI test helpers.

These are potential flakes found by static audit. I did not reproduce them. Several e2e specs require a Coder license, so validation below is written as targeted commands for the owner to run in an appropriately licensed environment.

## Files inspected

- `/home/openclaw/coder/site/AGENTS.md`
- `/home/openclaw/coder/.claude/docs/TESTING.md`
- `/home/openclaw/coder/site/e2e/playwright.config.ts`
- `/home/openclaw/coder/site/e2e/tests/organizations.spec.ts`
- `/home/openclaw/coder/site/e2e/tests/organizations/idpGroupSync.spec.ts`
- `/home/openclaw/coder/site/e2e/tests/organizations/idpRoleSync.spec.ts`
- `/home/openclaw/coder/site/e2e/tests/deployment/idpOrgSync.spec.ts`
- `/home/openclaw/coder/site/e2e/tests/templates/updateTemplateSchedule.spec.ts`
- `/home/openclaw/coder/site/e2e/tests/updateTemplate.spec.ts`
- `/home/openclaw/coder/site/e2e/tests/workspaces/autoCreateWorkspace.spec.ts`
- `/home/openclaw/coder/site/e2e/tests/workspaces/createWorkspace.spec.ts`
- `/home/openclaw/coder/site/src/modules/workspaces/DynamicParameter/DynamicParameter.test.tsx`
- Static inventory searched 39 Playwright `.spec.ts`, 71 React `.test.tsx`, 122 frontend `.test.ts`, and 200 Storybook `.stories.tsx` files under `/home/openclaw/coder/site`.

## Findings

### Fixed sleeps hide readiness in organization and IdP selector flows

- Category: `timing/eventual consistency`, `browser/e2e/playwright`
- Evidence:
  - `/home/openclaw/coder/site/e2e/tests/organizations.spec.ts:51-56` clicks `Delete this organization`, confirms the dialog, then uses `await page.waitForTimeout(1000)` before asserting `deleted successfully`.
  - `/home/openclaw/coder/site/e2e/tests/organizations/idpGroupSync.spec.ts:161-170` clicks the group selector, sleeps for 1000 ms, then waits up to 30 seconds for the `Everyone` option.
  - `/home/openclaw/coder/site/e2e/tests/organizations/idpRoleSync.spec.ts:138-152` clicks a role selector, clicks `page.getByRole("combobox")`, sleeps for 1000 ms, then waits for `Organization Admin`.
  - `/home/openclaw/coder/site/e2e/tests/deployment/idpOrgSync.spec.ts:158-167` clicks the org selector, sleeps for 1000 ms, then waits for the created organization option.
- Why it can flake: The sleep is not tied to the UI or API condition that matters. On a loaded CI runner, the option list or deletion toast can appear after 1 second. On a fast runner, the sleep only slows the suite while still leaving the real wait to a later generic assertion. The broad `combobox` click in the role test also risks targeting the wrong combobox if another control is present or added later.
- Proposed fix: Replace each `waitForTimeout(1000)` with a locator or response wait for the specific state. Examples: after deletion, wait for the delete API response and final toast; for selectors, click the specific selector locator and use `await expect(page.getByRole("option", { name: ... })).toBeVisible()` without a preceding sleep. In `idpRoleSync.spec.ts`, avoid the extra `page.getByRole("combobox").click()` and operate through the `roleSelector` locator.
- Validation: `cd /home/openclaw/coder/site && pnpm playwright:test e2e/tests/organizations.spec.ts e2e/tests/organizations/idpGroupSync.spec.ts e2e/tests/organizations/idpRoleSync.spec.ts e2e/tests/deployment/idpOrgSync.spec.ts --repeat-each=20 --workers=2`
- Historical references: `/home/openclaw/coder-flake-research/categories/timing-eventual-consistency.md:13-20` says larger waits often hide missing synchronization and recommends polling the actual condition with last observed state. `/home/openclaw/coder-flake-research/notes/common-solutions.md:11-16` calls replacing sleeps with deterministic synchronization a cross-category theme. `/home/openclaw/coder-flake-research/notes/common-solutions.md:153-160` lists frontend flakes from transient UI state, ambiguous selectors, and navigation before the page settled.

### `DynamicParameter` tests wrap `userEvent` in retry loops with no assertion

- Category: `browser/e2e/playwright`, `timing/eventual consistency`
- Evidence:
  - `/home/openclaw/coder/site/src/modules/workspaces/DynamicParameter/DynamicParameter.test.tsx:194-201` wraps `await userEvent.click(select)` in `await waitFor(async () => { ... })`, then asserts options.
  - `/home/openclaw/coder/site/src/modules/workspaces/DynamicParameter/DynamicParameter.test.tsx:214-221` wraps the select click in `waitFor`, then wraps the option click in another `waitFor`.
  - The same pattern repeats for radio, checkbox, switch, tags input, multi-select open, option select, and remove operations at lines `277-279`, `308-310`, `349-351`, `429-431`, `526-533`, and `548-550`.
- Why it can flake: `waitFor` retries when the callback throws. A pure `userEvent.click` or `userEvent.type` callback with no assertion usually succeeds on the first pass, so the wrapper does not wait for component state. If the callback does throw during a transient state, `waitFor` can repeat the user action and toggle state twice, click a closing menu, type duplicate input, or remove the wrong chip. This is a classic false synchronization smell.
- Proposed fix: Perform the user action once, then wait on the resulting observable state. Use `const user = userEvent.setup(); await user.click(select); await expect(screen.getByRole("option", { name: "Option 2" })).toBeVisible();` or `await screen.findByRole(...)`. For stateful controls, assert checked/value state after the action rather than retrying the action.
- Validation: `cd /home/openclaw/coder/site && pnpm test -- src/modules/workspaces/DynamicParameter/DynamicParameter.test.tsx --runInBand --repeat-each=20`
- Historical references: `/home/openclaw/coder-flake-research/categories/browser-e2e-playwright.md:15-20` recommends stable selectors and settled UI state. `/home/openclaw/coder-flake-research/categories/timing-eventual-consistency.md:121-127` references PR #24480, which removed redundant `waitFor` around `userEvent` in `CreateWorkspacePage.test.tsx` because it did not actually synchronize state.

### Parallel template update specs share a non-unique template name

- Category: `test isolation/order dependency`
- Evidence:
  - `/home/openclaw/coder/site/e2e/tests/updateTemplate.spec.ts:13` marks the file `test.describe.configure({ mode: "parallel" });`.
  - `/home/openclaw/coder/site/e2e/tests/templates/updateTemplateSchedule.spec.ts:26-29` creates a template with the fixed name `test-template` and display name `Test Template`.
  - `/home/openclaw/coder/site/e2e/playwright.config.ts:44-49` runs all `tests/**/*.spec.ts` in the same `tests` project after setup, with no per-file isolated coderd server.
- Why it can flake: Coder template names are unique per organization. If tests share the same seeded organization or if a retry leaves state behind, a fixed template name can collide with another spec or a prior attempt. The audited suite already uses `randomName()` for organizations in nearby specs, which makes this fixed template name stand out as unnecessary shared identity.
- Proposed fix: Generate a unique template name for this spec, for example `const templateName = randomName();`, then use that name in the template creation and URL/assertion paths. If display name matters, include the random suffix there too. Prefer deriving all externally visible org, user, workspace, and template names from the existing e2e `randomName()` helper.
- Validation: `cd /home/openclaw/coder/site && pnpm playwright:test e2e/tests/templates/updateTemplateSchedule.spec.ts e2e/tests/updateTemplate.spec.ts --repeat-each=20 --workers=4`
- Historical references: `/home/openclaw/coder-flake-research/categories/test-isolation-order-dependency.md:15-21` recommends generating unique users, orgs, workspace names, ports, paths, and DB rows per test. `/home/openclaw/coder-flake-research/categories/test-isolation-order-dependency.md:83-90` includes historical duplicate user and shared resource flakes, including issue #2709 and PR #2730. `/home/openclaw/coder-flake-research/notes/common-solutions.md:342-350` calls reused usernames, ports, temp paths, generated credentials, contexts, HTTP transports, deployments, mock providers, and global environment a recurring root cause.

### E2E web server depends on real Google OIDC discovery

- Category: `external service/dependency`, `browser/e2e/playwright`
- Evidence:
  - `/home/openclaw/coder/site/e2e/playwright.config.ts:151-158` configures the e2e server with `CODER_OIDC_ISSUER_URL: "https://accounts.google.com"` while other GitHub auth endpoints in the same config point at local fake URLs on lines `117-147`.
  - The e2e test inventory includes OIDC and IDP sync specs under `/home/openclaw/coder/site/e2e/tests/deployment/` and `/home/openclaw/coder/site/e2e/tests/organizations/` that exercise auth and sync UI flows.
- Why it can flake: If coderd performs OIDC discovery or JWKS fetches against `accounts.google.com` during e2e setup or a specific auth path, PR CI now depends on external DNS, Google availability, TLS, and rate limits. Most surrounding auth config is already local fake infrastructure, so this remote issuer is the outlier.
- Proposed fix: Replace the OIDC issuer with a local fake OIDC discovery/JWKS server in the e2e harness, or make tests that require real Google discovery explicitly quarantined with owner, issue, and expiry metadata. If the current tests never hit discovery, add a comment or preflight assertion proving the remote URL is inert so future tests do not accidentally depend on it.
- Validation: `cd /home/openclaw/coder/site && env -u HTTPS_PROXY -u HTTP_PROXY pnpm playwright:test e2e/tests/deployment e2e/tests/organizations --repeat-each=10 --workers=2`
- Historical references: `/home/openclaw/coder-flake-research/notes/common-solutions.md:14` says to prefer local fakes over real external systems. `/home/openclaw/coder-flake-research/categories/browser-e2e-playwright.md:15-21` includes browser dependency setup and artifacts as common fixes. `/home/openclaw/coder-flake-research/categories/external-service-dependency.md` classifies upstream latency, credentials, DNS, and transient network failures as nondeterministic CI inputs.

## Clean patterns / non-findings

- Playwright failure artifacts are configured. `/home/openclaw/coder/site/e2e/playwright.config.ts:60-65` retains screenshots, traces, and video on failure, and `/home/openclaw/coder/site/AGENTS.md:42-53` documents where to find local and CI artifacts. This matches the browser flake guidance.
- Git auth e2e endpoints are mostly local fakes. `/home/openclaw/coder/site/e2e/playwright.config.ts:117-147` routes token, device code, validate, and auth URLs through `localURL(...)`, reducing external GitHub dependency risk for those paths.
- Many entity-creating e2e specs already use `randomName()`, for example `/home/openclaw/coder/site/e2e/tests/organizations.spec.ts:21` and `/home/openclaw/coder/site/e2e/tests/organizations.spec.ts:36`. The hardcoded template name finding is not a blanket critique of the suite.
- I did not flag `waitUntil: "domcontentloaded"` by itself. It is common in the suite and only actionable when paired with assertions against stale React Query data, transient redirects, or missing final state waits.

## Next steps

1. Remove the fixed sleeps in the four organization and IdP specs first. They are the smallest, highest-confidence cleanup.
2. Refactor `DynamicParameter.test.tsx` to action once and wait on observable state. This should be mechanical and can use PR #24480 as the pattern.
3. Make `updateTemplateSchedule.spec.ts` use a unique template name, then run it next to the parallel template update spec under repeated workers.
4. Decide whether the Google OIDC issuer is intentionally remote. If not, add a fake issuer to the e2e harness before more OIDC paths grow around the current config.
