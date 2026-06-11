# Contributing to Ship Tracker

Thanks for contributing. Keep changes focused, tested, and production-minded.

## Workflow

1. Create a feature branch from `main`.
2. Make small, reviewable commits.
3. Run tests before opening a pull request.
4. Open a PR with context, risk notes, and verification steps.

## Local Validation

- Backend tests: run `pytest` from repository root.
- Frontend sanity check: ensure `npm run dev` starts in `frontend/`.
- Verify API docs load at `/docs` when backend is running.

## Coding Expectations

- Prefer clear names and small functions.
- Preserve existing architecture and conventions.
- Avoid unrelated refactors in feature/fix PRs.
- Include or update docs when behavior changes.

## Pull Request Checklist

- [ ] Scope is focused and clearly described.
- [ ] Tests added/updated when needed.
- [ ] Existing tests pass locally.
- [ ] No secrets or local-only files committed.
- [ ] README/docs updated (if needed).
