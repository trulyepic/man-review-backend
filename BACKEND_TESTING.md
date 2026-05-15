# Backend Testing

## Local Test Command

Install development dependencies, then run pytest:

```bash
pip install -r requirements-dev.txt
pytest
```

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
