# Backend CI/CD Rollout TODO

This checklist mirrors the frontend rollout: small branches, one clear improvement at a time, and no broad rewrites mixed into CI work.

## Current Backend Shape

- Python/FastAPI app under `app/`.
- Dependency list is `requirements.txt`.
- No backend test suite is currently present.
- No backend GitHub Actions workflow is currently present.
- Deployment is expected to remain Railway-driven unless we later decide to add GitHub deployment visibility.

## Phase 1: Backend Health Baseline

Suggested branch: `backend-ci-phase-1-health-baseline`

- [x] Add a minimal backend health/import check that can run without a live database.
- [x] Add `pytest` and a basic test layout if it is not already available.
- [x] Add first smoke tests for stable public endpoints or app creation.
- [x] Confirm the backend can be imported in CI without requiring production secrets.
- [x] Document which environment variables are required only at runtime.

## Phase 2: Lint And Formatting Baseline

Suggested branch: `backend-ci-phase-2-lint-format`

- [ ] Add a Python linter/formatter setup, likely Ruff.
- [ ] Keep the initial scope conservative: catch obvious syntax/import/style problems first.
- [ ] Avoid large formatting churn unless the codebase is already close to compliant.
- [ ] Add convenient local commands for linting.
- [ ] Confirm lint passes locally.

## Phase 3: Backend GitHub Actions CI

Suggested branch: `backend-ci-phase-3-github-actions`

- [ ] Add `.github/workflows/backend-ci.yml`.
- [ ] Run on pull requests to `main`.
- [ ] Run on pushes to `main`.
- [ ] Use a current Python version compatible with Railway.
- [ ] Install dependencies from `requirements.txt`.
- [ ] Run lint, tests/import checks, and any syntax checks as separate jobs where useful.

## Phase 4: Branch Protection Setup

Manual GitHub setup after Phase 3 is merged.

- [ ] Add backend CI checks to the `main` branch ruleset.
- [ ] Require pull requests before merging.
- [ ] Require passing backend checks before merging.
- [ ] Keep required approvals at `0` unless you want review enforcement later.

## Phase 5: Railway Deployment Visibility

Suggested branch: `backend-cd-railway-visibility`

- [ ] Decide whether Railway deployment status should appear in GitHub Actions.
- [ ] Prefer a read-only deployment-status check if Railway supports it cleanly.
- [ ] Avoid storing broad or long-lived credentials unless there is no better option.
- [ ] Document any required GitHub variables/secrets before enabling the job.

## Later

- [ ] Add deeper route tests with mocked dependencies.
- [ ] Add database-backed integration tests using a disposable test database.
- [ ] Add coverage reporting only after tests cover meaningful behavior.
- [ ] Clean encoding/mojibake comments in touched files when doing nearby maintenance.
- [ ] Consider backend security scanning once the basic CI foundation is stable.
