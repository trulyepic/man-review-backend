import uuid
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.routes import reading_list_routes


client = TestClient(app)
SHARE_TOKEN = uuid.UUID("11111111-1111-1111-1111-111111111111")


class FakeScalarResult:
    def __init__(self, *, rows=None, first=None):
        self._rows = rows or []
        self._first = first

    def all(self):
        return self._rows

    def first(self):
        return self._first


class FakeExecuteResult:
    def __init__(self, *, rows=None, first=None, scalar_one=None):
        self._rows = rows or []
        self._first = first
        self._scalar_one = scalar_one

    def scalars(self):
        return FakeScalarResult(rows=self._rows, first=self._first)

    def scalar_one(self):
        return self._scalar_one


class FakeReadingListSession:
    def __init__(self, results):
        self._results = list(results)
        self.added = []
        self.committed = False
        self.refreshed = []

    async def execute(self, _stmt):
        return self._results.pop(0)

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        self.committed = True

    async def refresh(self, item):
        self.refreshed.append(item)
        if getattr(item, "id", None) is None:
            item.id = 1
        if getattr(item, "is_public", None) is None:
            item.is_public = False
        if getattr(item, "share_token", None) is None:
            item.share_token = SHARE_TOKEN
        if getattr(item, "items", None) is None:
            item.items = []


def list_object(*, list_id=1, name="Favorites", items=None, is_public=False):
    return SimpleNamespace(
        id=list_id,
        name=name,
        is_public=is_public,
        share_token=SHARE_TOKEN,
        items=items or [],
    )


def item_object(*, series_id=25, left_off_chapter=None):
    return SimpleNamespace(series_id=series_id, left_off_chapter=left_off_chapter)


def override_reading_list_dependencies(session, *, user=None):
    current_user = user or SimpleNamespace(id=10, role="GENERAL")

    async def fake_get_db():
        yield session

    async def fake_current_user():
        return current_user

    app.dependency_overrides[reading_list_routes.get_db] = fake_get_db
    app.dependency_overrides[reading_list_routes.get_current_user] = fake_current_user

    def cleanup():
        app.dependency_overrides.pop(reading_list_routes.get_db, None)
        app.dependency_overrides.pop(reading_list_routes.get_current_user, None)

    return cleanup


def override_reading_list_db(session):
    async def fake_get_db():
        yield session

    app.dependency_overrides[reading_list_routes.get_db] = fake_get_db
    return lambda: app.dependency_overrides.pop(reading_list_routes.get_db, None)


def test_normalize_left_off_chapter_strips_empty_and_truncates():
    long_chapter = "  " + ("chapter-" * 10) + "  "

    assert reading_list_routes.normalize_left_off_chapter(None) is None
    assert reading_list_routes.normalize_left_off_chapter("   ") is None
    assert reading_list_routes.normalize_left_off_chapter("  Chapter 12  ") == "Chapter 12"
    assert len(reading_list_routes.normalize_left_off_chapter(long_chapter)) == 50


def test_create_reading_list_creates_list_for_current_user():
    full_list = list_object(name="Weekend Reads")
    session = FakeReadingListSession(
        [
            FakeExecuteResult(scalar_one=0),
            FakeExecuteResult(first=None),
            FakeExecuteResult(first=full_list),
        ]
    )
    cleanup = override_reading_list_dependencies(session)

    try:
        response = client.post("/reading-lists", json={"name": "Weekend Reads"})
    finally:
        cleanup()

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "name": "Weekend Reads",
        "is_public": False,
        "share_token": str(SHARE_TOKEN),
        "items": [],
    }
    assert session.committed is True
    assert len(session.added) == 1
    assert session.added[0].user_id == 10
    assert session.added[0].name == "Weekend Reads"


def test_create_reading_list_rejects_user_list_limit():
    session = FakeReadingListSession([FakeExecuteResult(scalar_one=2)])
    cleanup = override_reading_list_dependencies(session)

    try:
        response = client.post("/reading-lists", json={"name": "Third List"})
    finally:
        cleanup()

    assert response.status_code == 400
    assert response.json()["detail"] == "You can only create up to 2 lists."
    assert session.added == []
    assert session.committed is False


def test_add_series_to_list_adds_item_when_series_exists():
    updated_list = list_object(
        items=[item_object(series_id=25, left_off_chapter="Chapter 9")]
    )
    session = FakeReadingListSession(
        [
            FakeExecuteResult(first=list_object()),
            FakeExecuteResult(scalar_one=1),
            FakeExecuteResult(first=None),
            FakeExecuteResult(scalar_one=0),
            FakeExecuteResult(first=updated_list),
        ]
    )
    cleanup = override_reading_list_dependencies(session)

    try:
        response = client.post(
            "/reading-lists/1/items",
            json={"series_id": 25, "left_off_chapter": "  Chapter 9  "},
        )
    finally:
        cleanup()

    assert response.status_code == 200
    assert response.json()["items"] == [
        {"series_id": 25, "left_off_chapter": "Chapter 9"}
    ]
    assert session.committed is True
    assert len(session.added) == 1
    assert session.added[0].list_id == 1
    assert session.added[0].series_id == 25
    assert session.added[0].left_off_chapter == "Chapter 9"


def test_add_series_to_list_rejects_full_non_admin_list():
    session = FakeReadingListSession(
        [
            FakeExecuteResult(first=list_object()),
            FakeExecuteResult(scalar_one=1),
            FakeExecuteResult(first=None),
            FakeExecuteResult(scalar_one=35),
        ]
    )
    cleanup = override_reading_list_dependencies(session)

    try:
        response = client.post("/reading-lists/1/items", json={"series_id": 25})
    finally:
        cleanup()

    assert response.status_code == 400
    assert "List is full" in response.json()["detail"]
    assert session.added == []
    assert session.committed is False


def test_get_public_list_by_token_returns_public_list():
    public_list = list_object(
        name="Shared Reads",
        is_public=True,
        items=[item_object(series_id=7, left_off_chapter="Episode 4")],
    )
    session = FakeReadingListSession([FakeExecuteResult(first=public_list)])
    cleanup = override_reading_list_db(session)

    try:
        response = client.get(f"/reading-lists/public/{SHARE_TOKEN}")
    finally:
        cleanup()

    assert response.status_code == 200
    assert response.json() == {
        "name": "Shared Reads",
        "items": [{"series_id": 7, "left_off_chapter": "Episode 4"}],
    }
