---
name: add-api-endpoint-with-tests
description: Workflow command scaffold for add-api-endpoint-with-tests in aigc-reducer.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /add-api-endpoint-with-tests

Use this workflow when working on **add-api-endpoint-with-tests** in `aigc-reducer`.

## Goal

Adds a new API endpoint including router logic and integration tests.

## Common Files

- `web/src/aigc_web/routers/*.py`
- `web/src/aigc_web/main.py`
- `web/tests/test_*.py`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Create or update a router file in web/src/aigc_web/routers/ (e.g., auth.py)
- Update web/src/aigc_web/main.py to include the new router if needed
- Add or update a test file in web/tests/ (e.g., test_auth_router.py)

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.