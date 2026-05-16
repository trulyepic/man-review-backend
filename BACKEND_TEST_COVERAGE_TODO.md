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

- [x] Add tests for `/health`.
- [x] Add public sitemap route tests with mocked database/session behavior.
- [x] Add public series route tests where response behavior can be tested without production data.

## Phase 3: Auth And Security Helpers

Suggested branch: `backend-tests-phase-3-auth-security`

- [x] Add password hashing/login helper tests where practical.
- [x] Add email token tests.
- [x] Add captcha helper tests with mocked network responses.
- [x] Add admin dependency tests.

## Phase 4: Route Tests With Mocked Dependencies

Suggested branch: `backend-tests-phase-4-route-mocks`

- [x] Add route tests for reading lists with mocked sessions.
- [x] Add route tests for signup/login password behavior with mocked sessions.
- [x] Add route tests for issues with mocked sessions.
- [x] Add route tests for forum behavior with mocked sessions.
- [ ] Add route tests for media validation without touching S3.

## Phase 5: Database Integration Tests

Suggested branch: `backend-tests-phase-5-db-integration`

- [ ] Decide on disposable Postgres strategy for CI.
- [ ] Add test database setup/teardown.
- [ ] Add integration tests for core CRUD flows.
- [ ] Keep production database credentials out of tests.

## Later

- [ ] Add coverage reporting once tests cover meaningful behavior.
- [ ] Add JUnit pytest reports and upload them in GitHub Actions for clearer per-test failure summaries.
- [ ] Add regression tests when production bugs are found.
