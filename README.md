# coder-flake

Research workspace for nondeterministic test flakes in [`coder/coder`](https://github.com/coder/coder).

A "flake" here means a test or CI failure that is nondeterministic. It is not a Nix flake.

## Goals

1. Download GitHub issues and PRs related to flakes.
2. Categorize flakes by failure mode.
3. Identify common fixes Coder has already used.
4. Propose higher-leverage strategies to reduce CI flakiness.

## Current seed dataset

The first seed corpus is title-based GitHub Search data:

- `repo:coder/coder type:issue flake in:title`
- `repo:coder/coder type:issue flaky in:title`
- `repo:coder/coder type:pr flake in:title`
- `repo:coder/coder type:pr flaky in:title`

Downloaded artifacts:

- `raw/manifest.json`
- `raw/all-title-matches.json`
- `processed/title_matches.csv`

Verified seed count:

- 552 unique records
- 219 issues
- 333 PRs

## Next steps

The title search is only a seed. The next ingestion pass should expand via:

- issue comments
- timelines and cross references
- PR bodies that mention flake issue numbers
- PR files and test paths
- closing or fixing references

GitHub unauthenticated limits are tight. Use a read-only token or deploy-key-backed git access where possible, and make ingestion resumable.
