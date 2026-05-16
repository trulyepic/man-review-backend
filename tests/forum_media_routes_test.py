import io
from types import SimpleNamespace

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.models.forum_media_model import ForumMedia
from app.routes import forum_media_routes


client = TestClient(app)


class FakeForumMediaSession:
    def __init__(self):
        self.added = []
        self.committed = False
        self.refreshed = []

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        self.committed = True

    async def refresh(self, item):
        self.refreshed.append(item)
        if getattr(item, "id", None) is None:
            item.id = 1


def make_image_bytes(*, size=(16, 16), image_format="PNG"):
    buffer = io.BytesIO()
    Image.new("RGB", size, color=(32, 96, 160)).save(buffer, format=image_format)
    return buffer.getvalue()


def override_forum_media_dependencies(session, *, user=None):
    current_user = user or SimpleNamespace(id=10, username="reader", role="GENERAL")

    async def fake_get_db():
        yield session

    async def fake_current_user():
        return current_user

    app.dependency_overrides[forum_media_routes.get_async_session] = fake_get_db
    app.dependency_overrides[forum_media_routes.get_current_user] = fake_current_user

    def cleanup():
        app.dependency_overrides.pop(forum_media_routes.get_async_session, None)
        app.dependency_overrides.pop(forum_media_routes.get_current_user, None)

    return cleanup


def test_sniff_image_dims_returns_dimensions_for_valid_image():
    assert forum_media_routes.sniff_image_dims(make_image_bytes(size=(12, 8))) == (12, 8)
    assert forum_media_routes.sniff_image_dims(b"not an image") is None


def test_upload_forum_image_rejects_unsupported_mime_without_s3(monkeypatch):
    session = FakeForumMediaSession()
    cleanup = override_forum_media_dependencies(session)
    monkeypatch.setattr(
        forum_media_routes,
        "upload_to_s3",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("S3 called")),
    )

    try:
        response = client.post(
            "/forum/media/upload",
            data={"thread_id": "1"},
            files={"file": ("note.txt", b"hello", "text/plain")},
        )
    finally:
        cleanup()

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported image type."
    assert session.added == []


def test_upload_forum_image_rejects_empty_file_without_s3(monkeypatch):
    session = FakeForumMediaSession()
    cleanup = override_forum_media_dependencies(session)
    monkeypatch.setattr(
        forum_media_routes,
        "upload_to_s3",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("S3 called")),
    )

    try:
        response = client.post(
            "/forum/media/upload",
            data={"thread_id": "1"},
            files={"file": ("empty.png", b"", "image/png")},
        )
    finally:
        cleanup()

    assert response.status_code == 400
    assert response.json()["detail"] == "Empty file."
    assert session.added == []


def test_upload_forum_image_rejects_large_image_without_s3(monkeypatch):
    session = FakeForumMediaSession()
    cleanup = override_forum_media_dependencies(session)
    monkeypatch.setattr(
        forum_media_routes,
        "upload_to_s3",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("S3 called")),
    )

    try:
        response = client.post(
            "/forum/media/upload",
            data={"thread_id": "1"},
            files={
                "file": (
                    "large.png",
                    b"x" * (forum_media_routes.MAX_BYTES_IMAGE + 1),
                    "image/png",
                )
            },
        )
    finally:
        cleanup()

    assert response.status_code == 400
    assert response.json()["detail"] == "Image too large (max 300 KB)."
    assert session.added == []


def test_upload_forum_image_rejects_large_dimensions_without_s3(monkeypatch):
    session = FakeForumMediaSession()
    cleanup = override_forum_media_dependencies(session)
    monkeypatch.setattr(forum_media_routes, "sniff_image_dims", lambda _blob: (1025, 16))
    monkeypatch.setattr(
        forum_media_routes,
        "upload_to_s3",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("S3 called")),
    )

    try:
        response = client.post(
            "/forum/media/upload",
            data={"thread_id": "1"},
            files={"file": ("wide.png", make_image_bytes(), "image/png")},
        )
    finally:
        cleanup()

    assert response.status_code == 400
    assert response.json()["detail"] == "Image dimensions too large (max 1024×1024)."
    assert session.added == []


def test_upload_forum_image_persists_metadata_with_mocked_s3(monkeypatch):
    session = FakeForumMediaSession()
    cleanup = override_forum_media_dependencies(session)
    image_bytes = make_image_bytes(size=(20, 10))
    uploaded = []

    def fake_upload(fileobj, filename, content_type, folder, subfolder):
        uploaded.append(
            {
                "bytes": fileobj.read(),
                "filename": filename,
                "content_type": content_type,
                "folder": folder,
                "subfolder": subfolder,
            }
        )
        return "https://cdn.example.com/forum/media/upload.png"

    monkeypatch.setattr(forum_media_routes, "upload_to_s3", fake_upload)

    try:
        response = client.post(
            "/forum/media/upload",
            data={"thread_id": "1", "post_id": "5"},
            files={"file": ("upload.png", image_bytes, "image/png")},
        )
    finally:
        cleanup()

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "url": "https://cdn.example.com/forum/media/upload.png",
        "mime": "image/png",
        "size": len(image_bytes),
        "width": 20,
        "height": 10,
        "thread_id": 1,
        "post_id": 5,
    }
    assert uploaded == [
        {
            "bytes": image_bytes,
            "filename": "upload.png",
            "content_type": "image/png",
            "folder": "forum",
            "subfolder": "media",
        }
    ]
    assert session.committed is True
    assert len(session.added) == 1
    assert isinstance(session.added[0], ForumMedia)
    assert session.added[0].user_id == 10
    assert session.added[0].thread_id == 1
    assert session.added[0].post_id == 5
