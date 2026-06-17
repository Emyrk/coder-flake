# Not a test flake: Nix flake or maintenance

These references matched the word flake, but they are about `flake.nix`, `flake.lock`, update-flake automation, or dependency maintenance.

## Count

| references | issues | PRs |
| ---: | ---: | ---: |
| 41 | 3 | 38 |

## Why it flakes

Keep these out of nondeterministic test-flake metrics. They are useful CI maintenance signals, but they answer a different question.

## Common fixes

- Filter them out of test-flake dashboards.
- Track Nix maintenance separately if needed.
- Use the category as a false-positive bucket for search hygiene.

## Code examples

These examples are illustrative patterns for the category, not direct patches against one specific test.

<details>
<summary>Code examples</summary>

### Bad: mix Nix maintenance with test-flake counts

```sql
select count(*)
from github_references
where lower(title) like '%flake%';
```

### Better: filter false positives before reporting test flakes

```sql
select count(*)
from github_references
where category != 'not-a-test-flake/nix-flake-or-maintenance';
```

</details>

## Suggested first slice

Exclude this category from test-flake incident counts and keep it only as a search-quality note.

<details>
<summary>References (41)</summary>

| ref | type | title | status | evidence |
| --- | --- | --- | --- | --- |
| [issue #7834](https://github.com/coder/coder/issues/7834) | issue | add coder package derivation to nix flake | closed | add coder package derivation to nix flake It would be awesome to be able to install coder directly from this flake to get the latest version. In nixpkgs the coder version seems to still be at 0.17.1: https://search.nixos.org/packages?channel=unstable&from=0&size=50&sort=relevance&type=packages&query=coder Currently... |
| [issue #14343](https://github.com/coder/coder/issues/14343) | issue | Ensure all dependencies defined in `flake.nix` and our GitHub Actions are aligned | closed | Ensure all dependencies defined in `flake.nix` and our GitHub Actions are aligned For example, I'm having a hell of a time trying to generate some protobuf definitions which pass CI because `protoc-gen-go` is not locked in our nix flake, while it's using a fixed version in `.github/workflows/ci.yaml`. ```yaml - name... |
| [issue #26127](https://github.com/coder/coder/issues/26127) | issue | nix: flake.nix build fails - google-chrome-stable_138.0.7204.49 returns 404 from Google CDN | open | nix: flake.nix build fails - google-chrome-stable_138.0.7204.49 returns 404 from Google CDN ## Bug `nix develop` and `nix-shell shell.nix` fail on Linux because `google-chrome-stable_138.0.7204.49` has been deleted from Google's CDN. ## Environment - OS: Fedora - Nix flake nixpkgs pin: rev `50ab793` (flake.lock) - R... |
| [PR #6173](https://github.com/coder/coder/pull/6173) | PR | fix: Update flake.lock to fix Go build | closed; merged | fix: Update flake.lock to fix Go build Related: https://github.com/coder/coder/pull/5968 This PR fixes build problems with Go 1.20. I can see this error when I enter the `coder` directory. ``` ... while calling anonymous lambda at /nix/store/vgx3678yb41cb8g2g66nlj1alf3ksh92-source/pkgs/stdenv/generic/make-derivation... |
| [PR #8226](https://github.com/coder/coder/pull/8226) | PR | chore: update nix flake to include sqlc v1.18.0 | closed; merged | chore: update nix flake to include sqlc v1.18.0 Right now, I'm unable to develop Coder on Mac (which is my primary environment), as it fails due to lack of `sqlc.embed`: ``` $ make gen generate # package database queries/provisionerjobs.sql:51:1: function "sqlc.embed" does not exist make: *** [Makefile:490: coderd/d... |
| [PR #8645](https://github.com/coder/coder/pull/8645) | PR | chore: update nix flake to include sqlc v1.19.0 | closed; merged | chore: update nix flake to include sqlc v1.19.0 Spotted in https://github.com/coder/coder/pull/8644 `make gen` is failing on Mac with the following complain: ```bash make gen generate models.go:16:2: no required module provides package github.com/tabbed/pqtype; to add it: go get github.com/tabbed/pqtype make: *** [M... |
| [PR #8715](https://github.com/coder/coder/pull/8715) | PR | chore: update nix flake to include sqlc v1.19.1 | closed; merged | chore: update nix flake to include sqlc v1.19.1 Related: https://github.com/NixOS/nixpkgs/pull/245006 This PR updates dependency on sqlc v1.19.1 as currently `make gen` fails with: ``` generate models.go:16:2: no required module provides package github.com/tabbed/pqtype; to add it: go get github.com/tabbed/pqtype ma... |
| [PR #9197](https://github.com/coder/coder/pull/9197) | PR | chore(flake.nix): add gcloud and kubectl to flake | closed; merged | chore(flake.nix): add gcloud and kubectl to flake chore(flake.nix): add gcloud and kubectl to flake chore(flake.nix): add gcloud and kubectl to flake flake.lock flake.nix |
| [PR #9202](https://github.com/coder/coder/pull/9202) | PR | fix: add sapling to the nix flake | closed; merged | fix: add sapling to the nix flake fix: add sapling to the nix flake fix: add sapling to the nix flake flake.nix |
| [PR #9215](https://github.com/coder/coder/pull/9215) | PR | fix(flake.nix): add gcloud auth plugin | closed; merged | fix(flake.nix): add gcloud auth plugin fix(flake.nix): add gcloud auth plugin fix(flake.nix): add gcloud auth plugin flake.lock flake.nix |
| [PR #9219](https://github.com/coder/coder/pull/9219) | PR | chore(flake.nix): add kubectx | closed; merged | chore(flake.nix): add kubectx I ran the flake update command but it didn't produce any lockfile changes, is that correct? chore(flake.nix): add kubectx I ran the flake update command but it didn't produce any lockfile changes, is that correct? chore(flake.nix): add kubectx I ran the flake update command but it didn'... |
| [PR #9224](https://github.com/coder/coder/pull/9224) | PR | chore: add dependencies for js-test to our nix flake | closed; merged | chore: add dependencies for js-test to our nix flake chore: add dependencies for js-test to our nix flake chore: add dependencies for js-test to our nix flake flake.nix |
| [PR #10591](https://github.com/coder/coder/pull/10591) | PR | chore: fix flake.nix to run on macos | closed; merged | chore: fix flake.nix to run on macos strace is unavailable on macos. flake.nix is updated to handle this scenario. chore: fix flake.nix to run on macos strace is unavailable on macos. flake.nix is updated to handle this scenario. chore: fix flake.nix to run on macos strace is unavailable on macos. flake.nix is updat... |
| [PR #11529](https://github.com/coder/coder/pull/11529) | PR | chore(flake.nix): install mockgen from source | closed; not_merged | chore(flake.nix): install mockgen from source The stable package still points to the old repo. chore(flake.nix): install mockgen from source The stable package still points to the old repo. chore(flake.nix): install mockgen from source The stable package still points to the old repo. flake.nix <b>In this stack:</b>... |
| [PR #11537](https://github.com/coder/coder/pull/11537) | PR | chore: update flake to include new mockgen | closed; merged | chore: update flake to include new mockgen It looks like we updated mockgen to use Uber's fork, but the flake lockfile still pointed to a nixos-unstable commit that had the old mockgen resulting in an error like: missing go.sum entry for module providing package github.com/golang/mock/mockgen/model chore: update fla... |
| [PR #11716](https://github.com/coder/coder/pull/11716) | PR | fix: make yarn from nix flake use the right version of node | closed; merged | fix: make yarn from nix flake use the right version of node Otherwise if for example you try to run `yarn storybook` it complains that the version of Node is wrong. `pnpm storybook` works fine and maybe that is what we should actually use, but as long as we have yarn installed might as well make use the right thing.... |
| [PR #11974](https://github.com/coder/coder/pull/11974) | PR | fix(flake.nix): add google-chrome to nix flake | closed; merged | fix(flake.nix): add google-chrome to nix flake Required for scaletest tests. fix(flake.nix): add google-chrome to nix flake Required for scaletest tests. fix(flake.nix): add google-chrome to nix flake Required for scaletest tests. flake.nix I am not a nix expert but why do we need this? I think we install the headle... |
| [PR #13186](https://github.com/coder/coder/pull/13186) | PR | chore: add build targets to nix flake | closed; merged | chore: add build targets to nix flake Enables `nix build github:coder/coder[/branch]#linux_amd64`! chore: add build targets to nix flake Enables `nix build github:coder/coder[/branch]#linux_amd64`! chore: add build targets to nix flake Enables `nix build github:coder/coder[/branch]#linux_amd64`! .github/workflows/ci... |
| [PR #13243](https://github.com/coder/coder/pull/13243) | PR | fix: fix nix flake sed command | closed; merged | fix: fix nix flake sed command Seeing some errors: ``` Downloading Go modules... Calculating SRI hash... sed: -e expression #1, char 37: unknown option to `s' ``` [here](https://github.com/coder/coder/actions/runs/9036466674/job/24836282425?pr=13098) fix: fix nix flake sed command Seeing some errors: ``` Downloading... |
| [PR #13540](https://github.com/coder/coder/pull/13540) | PR | chore: Pin sqlc to v1.25.0 in `flake.nix` | closed; not_merged | chore: Pin sqlc to v1.25.0 in `flake.nix` chore: Pin sqlc to v1.25.0 in `flake.nix` chore: Pin sqlc to v1.25.0 in `flake.nix` flake.nix Can we just update to 1.26.0? Not sure why dogfood is failing here... just gonna close for now |
| [PR #13930](https://github.com/coder/coder/pull/13930) | PR | chore: update flake.nix to handle aarch64 linux | closed; merged | chore: update flake.nix to handle aarch64 linux `google-chrome` is not available for aarch64 linux https://search.nixos.org/packages?channel=unstable&show=google-chrome&from=0&size=50&sort=relevance&type=packages&query=google-chrome Also bumps terraform to 1.9.2 for nix. chore: update flake.nix to handle aarch64 lin... |
| [PR #14046](https://github.com/coder/coder/pull/14046) | PR | chore: add script to update flake automatically | closed; merged | chore: add script to update flake automatically chore: add script to update flake automatically chore: add script to update flake automatically .github/workflows/ci.yaml |
| [PR #14052](https://github.com/coder/coder/pull/14052) | PR | ci: handle retriggering ci and human authors in `update-flake` | closed; merged | ci: handle retriggering ci and human authors in `update-flake` This PR improves #14046 based on instructions [here](https://github.com/stefanzweifel/git-auto-commit-action#commits-made-by-this-action-do-not-trigger-new-workflow-runs). Should solve the CI stuck issue exhibited in - #14039 - #14040 - #14041 - #14044 c... |
| [PR #14067](https://github.com/coder/coder/pull/14067) | PR | fix: run update-flake with PAT to allow workflow runs | closed; merged | fix: run update-flake with PAT to allow workflow runs See the comment in the code. fix: run update-flake with PAT to allow workflow runs See the comment in the code. fix: run update-flake with PAT to allow workflow runs See the comment in the code. .github/workflows/ci.yaml |
| [PR #14091](https://github.com/coder/coder/pull/14091) | PR | chore: commit update-flake as @dependabot | closed; merged | chore: commit update-flake as @dependabot Thıs is needed to bypass the dependency check job for dependabot PRs as we add another commit to update-flake. For example, it will resolve the issue in #14041 https://github.com/coder/coder/blob/1289937eaeac63f27f2856a4374a0fedc5cc0e58/.github/workflows/ci.yaml#L973 The use... |
| [PR #14552](https://github.com/coder/coder/pull/14552) | PR | ci: extract update-flake to separate workflow | closed; not_merged | ci: extract update-flake to separate workflow ci: extract update-flake to separate workflow ci: extract update-flake to separate workflow .github/workflows/ci.yaml |
| [PR #14554](https://github.com/coder/coder/pull/14554) | PR | ci: disable update-flake in PRs | closed; merged | ci: disable update-flake in PRs Relates to https://github.com/coder/internal/issues/71 Disables the `update-flake` check in PRs. ci: disable update-flake in PRs Relates to https://github.com/coder/internal/issues/71 Disables the `update-flake` check in PRs. ci: disable update-flake in PRs Relates to https://github.c... |
| [PR #14728](https://github.com/coder/coder/pull/14728) | PR | chore: add ability to include custom protoc-gen-go dependency in nix flake | closed; merged | chore: add ability to include custom protoc-gen-go dependency in nix flake This PR can be a starting point to fix https://github.com/coder/coder/issues/14343 chore: add ability to include custom protoc-gen-go dependency in nix flake This PR can be a starting point to fix https://github.com/coder/coder/issues/14343 c... |
| [PR #15259](https://github.com/coder/coder/pull/15259) | PR | fix(flake.nix): remove `preBuild` to fix building on Linux | closed; merged | fix(flake.nix): remove `preBuild` to fix building on Linux On Linux, network access isn't available inside of a build. It seems to build correctly without this `preBuild` hook. See: https://github.com/coder/coder/pull/14728#issuecomment-2417775977 cc @joobisb ``` $ nix develop warning: Git tree '/home/colin/Projects... |
| [PR #16120](https://github.com/coder/coder/pull/16120) | PR | fix(flake.nix): install locales on linux host devShells | closed; merged | fix(flake.nix): install locales on linux host devShells Change-Id: I22dba63d317b41749c807a55e15278006cdcecad Signed-off-by: Thomas Kosiewski <tk@coder.com> - Adds neovim and fzf to development tools, removes sapling, and fixes locale issues on Linux systems. - Updates Dockerfile.nix syntax to use uppercase `AS` to r... |
| [PR #16153](https://github.com/coder/coder/pull/16153) | PR | fix(flake.nix): fix site build & add missing inputs for darwin hosts | closed; merged | fix(flake.nix): fix site build & add missing inputs for darwin hosts - update `flake.nix`: - use `devShells.default` instead of `devShell` - include macOS-specific build inputs - use the same nodejs version in the default devShell and pnpm frontend build - update `site/.npmrc` to include tarball URLs for a reproduci... |
| [PR #16154](https://github.com/coder/coder/pull/16154) | PR | fix(flake.nix): fix coder binary build | closed; merged | fix(flake.nix): fix coder binary build Change-Id: I2adc511dd7b4de4e221e74234ec1eae743589caf Signed-off-by: Thomas Kosiewski <tk@coder.com> fix(flake.nix): fix coder binary build Change-Id: I2adc511dd7b4de4e221e74234ec1eae743589caf Signed-off-by: Thomas Kosiewski <tk@coder.com> fix(flake.nix): fix coder binary build... |
| [PR #16162](https://github.com/coder/coder/pull/16162) | PR | fix(flake.nix): update lockfile & add nix-prefetch-git | closed; merged | fix(flake.nix): update lockfile & add nix-prefetch-git Updated flake.lock and flake.nix dependencies, including: - Updated flake.lock - Updated vendorHash for coder binary - Ensured pnpm 9.x uses nodejs 20 - Reordered development shell packages alphabetically Change-Id: I3e5e9c9d1136ea8d03084bd13fdd723bff1680d9 Sign... |
| [PR #16223](https://github.com/coder/coder/pull/16223) | PR | feat(flake.nix): switch dogfood dev image to buildNixShellImage from dockerTools | closed; merged | feat(flake.nix): switch dogfood dev image to buildNixShellImage from dockerTools Replace Depot build action with Nix for Nix dogfood image builds The dogfood Nix image is now built using Nix's native container tooling instead of Depot. This change: - Adds Nix setup steps to the GitHub Actions workflow - Removes the... |
| [PR #16318](https://github.com/coder/coder/pull/16318) | PR | fix(flake.nix): limit the amount of maximum layers to 32 on dogfood nix image | closed; merged | fix(flake.nix): limit the amount of maximum layers to 32 on dogfood nix image Adds maxLayers parameter to dev_image and inlines dockerTools functions Inlines relevant dockerTools functions from nixpkgs to support maxLayers configuration in dev_image. This prevents issues with sysbox on dogfood environments when imag... |
| [PR #16325](https://github.com/coder/coder/pull/16325) | PR | fix(flake.nix): include dev buildInputs in dogfood nix image | closed; merged | fix(flake.nix): include dev buildInputs in dogfood nix image Improve Nix shell environment in Dogfood Docker image - Pinned gcc to gcc13 in devShell - Add busybox, coreutils, curl, glibc, and binutils to dogfood nix image - Configure proper home directory and user settings in dogfood nix image - Set up dynamic libra... |
| [PR #16429](https://github.com/coder/coder/pull/16429) | PR | fix(flake.nix): readd grep for agent startup script | closed; merged | fix(flake.nix): readd grep for agent startup script Added `gnugrep` to the development shell dependencies, as its a dependency of the bootstrap script for an agent. Change-Id: Ia56e16a831bb94af2324e33ae5274833d0123d47 Signed-off-by: Thomas Kosiewski <tk@coder.com> fix(flake.nix): readd grep for agent startup script... |
| [PR #16607](https://github.com/coder/coder/pull/16607) | PR | fix(flake.nix): add procps to nix dogfood image | closed; merged | fix(flake.nix): add procps to nix dogfood image Add procps to flake.nix and release name to Docker image Adds the `procps` package to flake.nix to enable the `free` command, and includes a release name file in the Docker image at `/etc/coderniximage-release`. Change-Id: I85432acc06a204229fa3675e0020bd3acacf775a Sign... |
| [PR #16715](https://github.com/coder/coder/pull/16715) | PR | fix(flake.nix): synchronize playwright version in nix and package.json | closed; merged | fix(flake.nix): synchronize playwright version in nix and package.json Ensure that the version of Playwright installed with the Nix flake is equal to the one specified in `site/package.json.` -- This assertion ensures that `pnpm playwright:install` will not attempt to download newer browser versions not present in t... |
| [PR #20975](https://github.com/coder/coder/pull/20975) | PR | test: fix TestDescCacheTimestampUpdate flake | closed; merged | test: fix TestDescCacheTimestampUpdate flake ## Problem `TestDescCacheTimestampUpdate` was flaky on Windows CI because `time.Now()` has ~15.6ms resolution, causing consecutive calls to return identical timestamps. ## Solution Inject `quartz.Clock` into `MetricsAggregator` using an options pattern, making the test de... |
| [PR #25815](https://github.com/coder/coder/pull/25815) | PR | fix(flake.nix): stop forcing musl biome binary in dev shell | closed; merged | fix(flake.nix): stop forcing musl biome binary in dev shell The nix-shell environment currently forces `BIOME_BINARY` to the musl Biome package. On my Ubuntu 24.04 nix-shell, that breaks `pnpm exec biome` because `pnpm install` only installs the host-matching glibc Biome package by default, so the forced musl packag... |

</details>
