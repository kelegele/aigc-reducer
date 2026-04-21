---
name: add-backend-service-or-feature
description: Workflow command scaffold for add-backend-service-or-feature in aigc-reducer.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /add-backend-service-or-feature

Use this workflow when working on **add-backend-service-or-feature** in `aigc-reducer`.

## Goal

Implements a new backend service or feature, including the service logic and corresponding unit tests.

## Common Files

- `web/src/aigc_web/services/*.py`
- `web/tests/test_*.py`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Create or update a file in web/src/aigc_web/services/ (e.g., auth.py, sms.py, token.py)
- Create or update a corresponding test file in web/tests/ (e.g., test_auth_service.py, test_sms.py, test_token.py)

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.