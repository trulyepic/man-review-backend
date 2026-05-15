# Backend Test Coverage TODO

This roadmap expands backend tests in small branches. Each branch should add real tests plus any necessary documentation updates.

## Phase 1: Utility Tests

Suggested branch: `backend-tests-phase-1-utilities`

- [x] Add tests for JWT helper behavior.
- [x] Add tests for forum image URL validation.
- [x] Add tests for profanity detection.
- [x] Keep tests isolated from live database, S3, email, Google OAuth, and reCAPTCHA.

## Phase 2: Public Route Smoke Tests

Suggested branch: `backend-tests-phase-2-public-routes`

- [ ] Add tests for `/health`.
- [ ] Add public sitemap route tests with mocked database/session behavior.
- [ ] Add public series route tests where response behavior can be tested without production data.

## Phase 3: Auth And Security Helpers

Suggested branch: `backend-tests-phase-3-auth-security`

- [ ] Add password hashing/login helper tests where practical.
- [ ] Add email token tests.
- [ ] Add captcha helper tests with mocked network responses.
- [ ] Add admin dependency tests.

## Phase 4: Route Tests With Mocked Dependencies

Suggested branch: `backend-tests-phase-4-route-mocks`

- [ ] Add route tests for reading lists with mocked sessions.
- [ ] Add route tests for issues with mocked sessions.
- [ ] Add route tests for forum behavior with mocked sessions.
- [ ] Add route tests for media validation without touching S3.

## Phase 5: Database Integration Tests

Suggested branch: `backend-tests-phase-5-db-integration`

- [ ] Decide on disposable Postgres strategy for CI.
- [ ] Add test database setup/teardown.
- [ ] Add integration tests for core CRUD flows.
- [ ] Keep production database credentials out of tests.

## Later

- [ ] Add coverage reporting once tests cover meaningful behavior.
- [ ] Consider JUnit test reports in GitHub Actions for more clickable test summaries.
- [ ] Add regression tests when production bugs are found.
