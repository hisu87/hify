"""Tests for basic FastAPI router endpoints."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from downtify.api import check_update, get_version, router


def test_check_update_function_returns_none():
    assert check_update() is None


def test_version_function_returns_string():
    assert isinstance(get_version(), str)


def test_check_update_http_endpoint():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.get('/api/check_update')
    assert response.status_code == 200
    assert response.json() is None


def test_version_http_endpoint():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.get('/api/version')
    assert response.status_code == 200
    assert isinstance(response.json(), str)
