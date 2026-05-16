from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.routes import auth


client = TestClient(app)


class FakeScalarResult:
    def __init__(self, rows=None, one=None):
        self._rows = rows or []
        self._one = one

    def all(self):
        return self._rows

    def first(self):
        return self._one


class FakeExecuteResult:
    def __init__(self, rows=None, one=None):
        self._rows = rows or []
        self._one = one

    def scalars(self):
        return FakeScalarResult(rows=self._rows, one=self._one)

    def scalar_one_or_none(self):
        return self._one


class FakeAuthSession:
    def __init__(self, *, execute_result=None):
        self.execute_result = execute_result or FakeExecuteResult()
        self.added = []
        self.committed = False
        self.flushed = False
        self.refreshed = []
        self.rolled_back = False

    async def execute(self, _stmt):
        return self.execute_result

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        self.flushed = True

    async def commit(self):
        self.committed = True

    async def refresh(self, item):
        self.refreshed.append(item)
        if getattr(item, "id", None) is None:
            item.id = 1

    async def rollback(self):
        self.rolled_back = True


def override_auth_db(session):
    async def fake_get_db():
        yield session

    app.dependency_overrides[auth.get_db] = fake_get_db
    return lambda: app.dependency_overrides.pop(auth.get_db, None)


async def fake_verify_captcha(*args, **kwargs):
    return None


def test_signup_creates_unverified_user_with_normalized_email(monkeypatch):
    session = FakeAuthSession()
    cleanup = override_auth_db(session)
    sent_emails = []

    monkeypatch.setattr(auth, "verify_captcha", fake_verify_captcha)
    monkeypatch.setattr(auth, "generate_email_token", lambda email: f"token-for-{email}")
    monkeypatch.setattr(
        auth,
        "send_verification_email",
        lambda email, token: sent_emails.append((email, token)),
    )

    try:
        response = client.post(
            "/auth/signup",
            json={
                "username": "  NewReader  ",
                "password": "safe-password",
                "email": "Reader@Gmail.com",
                "captcha_token": "captcha-token",
            },
        )
    finally:
        cleanup()

    assert response.status_code == 200
    assert response.json() == {
        "message": "User created successfully. Please verify your email.",
        "token": "token-for-reader@gmail.com",
    }
    assert session.flushed is True
    assert session.committed is True
    assert session.rolled_back is False
    assert sent_emails == [("reader@gmail.com", "token-for-reader@gmail.com")]
    assert len(session.added) == 1
    assert session.added[0].username == "NewReader"
    assert session.added[0].email == "reader@gmail.com"
    assert session.added[0].is_verified is False
    assert auth.bcrypt.verify("safe-password", session.added[0].password)


def test_signup_rejects_existing_email(monkeypatch):
    existing = SimpleNamespace(username="OtherUser", email="reader@gmail.com")
    session = FakeAuthSession(execute_result=FakeExecuteResult(rows=[existing]))
    cleanup = override_auth_db(session)

    monkeypatch.setattr(auth, "verify_captcha", fake_verify_captcha)

    try:
        response = client.post(
            "/auth/signup",
            json={
                "username": "NewReader",
                "password": "safe-password",
                "email": "reader@gmail.com",
                "captcha_token": "captcha-token",
            },
        )
    finally:
        cleanup()

    assert response.status_code == 409
    assert response.json()["detail"] == "Email already exists"
    assert session.added == []


def test_signup_rolls_back_when_verification_email_fails(monkeypatch):
    session = FakeAuthSession()
    cleanup = override_auth_db(session)

    monkeypatch.setattr(auth, "verify_captcha", fake_verify_captcha)
    monkeypatch.setattr(auth, "generate_email_token", lambda email: "token")

    def fail_send(*args, **kwargs):
        raise RuntimeError("smtp unavailable")

    monkeypatch.setattr(auth, "send_verification_email", fail_send)

    try:
        response = client.post(
            "/auth/signup",
            json={
                "username": "NewReader",
                "password": "safe-password",
                "email": "reader@gmail.com",
                "captcha_token": "captcha-token",
            },
        )
    finally:
        cleanup()

    assert response.status_code == 500
    assert response.json()["detail"] == "Signup failed during email sending"
    assert session.rolled_back is True
    assert session.committed is False


def test_login_returns_access_token_for_verified_user(monkeypatch):
    db_user = SimpleNamespace(
        id=7,
        username="reader",
        password=auth.bcrypt.hash("safe-password"),
        is_verified=True,
        role="GENERAL",
    )
    session = FakeAuthSession(execute_result=FakeExecuteResult(one=db_user))
    cleanup = override_auth_db(session)

    monkeypatch.setattr(auth, "verify_captcha", fake_verify_captcha)
    monkeypatch.setattr(auth, "create_access_token", lambda user: f"token-for-{user.username}")

    try:
        response = client.post(
            "/auth/login",
            json={
                "username": "reader",
                "password": "safe-password",
                "captcha_token": "captcha-token",
            },
        )
    finally:
        cleanup()

    assert response.status_code == 200
    assert response.json() == {
        "access_token": "token-for-reader",
        "user": {"id": 7, "username": "reader", "role": "GENERAL"},
    }


def test_login_rejects_invalid_password(monkeypatch):
    db_user = SimpleNamespace(
        id=7,
        username="reader",
        password=auth.bcrypt.hash("safe-password"),
        is_verified=True,
        role="GENERAL",
    )
    session = FakeAuthSession(execute_result=FakeExecuteResult(one=db_user))
    cleanup = override_auth_db(session)

    monkeypatch.setattr(auth, "verify_captcha", fake_verify_captcha)

    try:
        response = client.post(
            "/auth/login",
            json={
                "username": "reader",
                "password": "wrong-password",
                "captcha_token": "captcha-token",
            },
        )
    finally:
        cleanup()

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_login_rejects_unverified_user(monkeypatch):
    db_user = SimpleNamespace(
        id=7,
        username="reader",
        password=auth.bcrypt.hash("safe-password"),
        is_verified=False,
        role="GENERAL",
    )
    session = FakeAuthSession(execute_result=FakeExecuteResult(one=db_user))
    cleanup = override_auth_db(session)

    monkeypatch.setattr(auth, "verify_captcha", fake_verify_captcha)

    try:
        response = client.post(
            "/auth/login",
            json={
                "username": "reader",
                "password": "safe-password",
                "captcha_token": "captcha-token",
            },
        )
    finally:
        cleanup()

    assert response.status_code == 403
    assert response.json()["detail"] == "Email not verified"
