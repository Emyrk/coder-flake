# Potential flake solutions

This directory is for audits of current `github.com/coder/coder` test code using the flake research corpus as the knowledge base.

Each solution note should include:

- Area reviewed
- Files inspected
- Potential flake findings with file and line evidence
- Category from the flake taxonomy
- Why it can fail nondeterministically
- Proposed fix
- Suggested validation command
- Relevant historical references from `categories/` or `processed/categories.csv`

These are proposals, not confirmed flakes, until reproduced with repeated test runs, race detector, CI evidence, or a targeted failing artifact.
