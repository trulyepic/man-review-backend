from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.deps.admin import can_submit_series, get_role_name, is_admin, require_admin, require_series_submitter

pytestmark = pytest.mark.anyio


def test_get_role_name_defaults_missing_role_to_general():
    assert get_role_name(SimpleNamespace()) == "GENERAL"


def test_is_admin_returns_true_for_admin_role():
    assert is_admin(SimpleNamespace(role="admin")) is True


def test_can_submit_series_allows_admin_and_contributor_roles():
    assert can_submit_series(SimpleNamespace(role="ADMIN")) is True
    assert can_submit_series(SimpleNamespace(role="CONTRIBUTOR")) is True


def test_can_submit_series_rejects_general_role():
    assert can_submit_series(SimpleNamespace(role="GENERAL")) is False


async def test_require_admin_returns_admin_user():
    user = SimpleNamespace(role="ADMIN")

    assert await require_admin(user) is user


async def test_require_admin_raises_for_non_admin_user():
    with pytest.raises(HTTPException) as exc_info:
        await require_admin(SimpleNamespace(role="GENERAL"))

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Admin access required"


async def test_require_series_submitter_returns_contributor_user():
    user = SimpleNamespace(role="CONTRIBUTOR")

    assert await require_series_submitter(user) is user


async def test_require_series_submitter_raises_for_general_user():
    with pytest.raises(HTTPException) as exc_info:
        await require_series_submitter(SimpleNamespace(role="GENERAL"))

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Contributor or admin access required"
