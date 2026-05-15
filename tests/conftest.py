import os

import pytest


def pytest_configure():
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql://toonranks_test:toonranks_test@localhost:5432/toonranks_test",
    )
    os.environ.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-characters")
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "test-access-key")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test-secret-key")
    os.environ.setdefault("AWS_REGION", "us-west-1")
    os.environ.setdefault("AWS_BUCKET_NAME", "toonranks-test")
    os.environ.setdefault("PUBLIC_ORIGIN", "https://www.toonranks.com")


@pytest.fixture
def anyio_backend():
    return "asyncio"
