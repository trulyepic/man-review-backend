# Backend Testing

## Local Test Command

Install development dependencies, then run pytest:

```bash
pip install -r requirements-dev.txt
pytest
```

Run the backend lint baseline:

```bash
ruff check .
```

## Integration Tests

Integration tests are marked with `@pytest.mark.integration` and require a disposable Postgres
database through `TEST_DATABASE_URL`.

Run only the normal mocked/unit test suite:

```bash
pytest -m "not integration"
```

Run integration tests locally only when you have a disposable test database ready:

```bash
set TEST_DATABASE_URL=postgresql+asyncpg://toonranks_test:toonranks_test@localhost:5432/toonranks_test
pytest -m integration
```

Never point `TEST_DATABASE_URL` at Railway, production, or any long-lived database. The integration
test setup creates and drops tables in the target database.

## CI Test Reports

GitHub Actions writes pytest JUnit XML reports for the unit and integration test jobs, then uploads
them as workflow artifacts:

- `backend-unit-test-report`
- `backend-integration-test-report`

The local `test-results/` folder is ignored by git, so you can generate reports locally without
accidentally committing them.

## Test Environment

The test suite sets safe dummy values in `tests/conftest.py` before importing the FastAPI app. This keeps smoke tests from depending on production Railway, Postgres, S3, email, Google OAuth, or reCAPTCHA settings.

## Runtime Environment Variables

These values are still required for the deployed backend runtime:

- `DATABASE_URL`
- `SECRET_KEY`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `AWS_BUCKET_NAME`

Feature-specific values may also be needed when those integrations are enabled:

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `FROM_EMAIL`
- `GOOGLE_CLIENT_ID`
- `RECAPTCHA_SECRET_KEY`
- `RECAPTCHA_SITE_KEY`
- `RECAPTCHA_PROJECT_ID`
