"""J2 — Caregiver register + profile (live DB)."""

import os

import pytest

pytestmark = [pytest.mark.sentinel_e2e, pytest.mark.j2]


def test_users_me_after_bootstrap(hub_client):
    r = hub_client.get("/api/users/me")
    assert r.status_code == 200
    data = r.json()
    expected_email = os.environ.get("E2E_USER_EMAIL", "e2e-caregiver@homecareguardian.test")
    assert data.get("email") == expected_email
    assert data.get("name")


def test_register_conflict_is_idempotent(hub_client):
    """Re-register same email must not break single-user hub."""
    r = hub_client.post(
        "/api/auth/register",
        json={
            "name": os.environ.get("E2E_USER_NAME", "E2E Caregiver"),
            "email": os.environ.get("E2E_USER_EMAIL", "e2e-caregiver@homecareguardian.test"),
            "password": os.environ.get("E2E_USER_PASSWORD", "E2eTestPassword123!"),
            "birth_year": 1950,
            "pronoun": "they",
            "postcode": "SW1A 1AA",
        },
    )
    assert r.status_code in (200, 201, 409)
