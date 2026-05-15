import pytest
from fastapi import HTTPException

from app.utils import forum_content


def test_reject_disallowed_images_accepts_https_markdown_image_url(monkeypatch):
    checked_urls = []

    def fake_head_check(url: str) -> None:
        checked_urls.append(url)

    monkeypatch.setattr(forum_content, "_best_effort_head_check", fake_head_check)

    forum_content.reject_disallowed_images("![cover](https://cdn.example.com/cover.webp)")

    assert checked_urls == ["https://cdn.example.com/cover.webp"]


def test_reject_disallowed_images_normalizes_protocol_relative_image_url(monkeypatch):
    checked_urls = []

    def fake_head_check(url: str) -> None:
        checked_urls.append(url)

    monkeypatch.setattr(forum_content, "_best_effort_head_check", fake_head_check)

    forum_content.reject_disallowed_images('<img src="//cdn.example.com/panel.jpg" />')

    assert checked_urls == ["https://cdn.example.com/panel.jpg"]


@pytest.mark.parametrize(
    ("markdown", "detail"),
    [
        ("![bad](javascript:alert(1))", "Only http(s) images are allowed"),
        ("![bad](https://cdn.example.com/file.svg)", "Unsupported image type"),
        ('<img src="https://cdn.example.com/file.txt" />', "Unsupported image type"),
    ],
)
def test_reject_disallowed_images_blocks_unsafe_sources(monkeypatch, markdown, detail):
    monkeypatch.setattr(forum_content, "_best_effort_head_check", lambda url: None)

    with pytest.raises(HTTPException) as exc_info:
        forum_content.reject_disallowed_images(markdown)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == detail
