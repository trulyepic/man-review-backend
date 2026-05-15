from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_app_imports_with_test_environment():
    assert app.title == "Toon Ranks API"


def test_health_check_returns_ok_response():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_redirect_www_redirects_bare_domain_to_www():
    response = client.get(
        "/health",
        headers={"host": "toonranks.com"},
        follow_redirects=False,
    )

    assert response.status_code == 301
    assert response.headers["location"] == "http://www.toonranks.com/health"


def test_redirect_www_skips_sitemap_paths_for_bare_domain():
    response = client.get(
        "/sitemap-not-real.xml",
        headers={"host": "toonranks.com"},
        follow_redirects=False,
    )

    assert response.status_code == 404
