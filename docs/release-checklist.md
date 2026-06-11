# Release Checklist

Use this checklist before tagging or shipping a release.

## Quality Gates

- [ ] Backend tests pass (`pytest`).
- [ ] Frontend build succeeds (`npm run build` in `frontend/`).
- [ ] Manual smoke test completed (map, vessel feed, alerts, incidents).

## Operational Readiness

- [ ] `backend/.env` keys validated for target environment.
- [ ] Database migrations/initialization steps verified.
- [ ] Redis and Celery worker/beat start cleanly.
- [ ] Health endpoint responds: `GET /api/health`.

## Data and Assets

- [ ] Large geospatial files are tracked with Git LFS when applicable.
- [ ] New static datasets documented in README or docs.

## Release Hygiene

- [ ] Version/changelog updated (if used).
- [ ] Security review complete (no accidental secrets).
- [ ] Rollback plan documented.
- [ ] Tag/release notes prepared.
