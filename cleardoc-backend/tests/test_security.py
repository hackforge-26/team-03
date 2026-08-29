import os

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SYNC_DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("SMTP_USER", "test@example.com")
os.environ.setdefault("SMTP_PASSWORD", "secret")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

import builtins
import importlib
import sys

from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_app_imports_without_optional_document_dependencies(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name in {"fitz", "pytesseract", "magic"}:
            raise ModuleNotFoundError(f"No module named '{name}'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    for module_name in ["app.main", "app.services.parser_service"]:
        sys.modules.pop(module_name, None)

    import app.main as main_module

    assert main_module.app is not None


def test_health_response_has_security_headers():
    response = client.get("/health")
    assert response.status_code in (200, 503)
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("content-security-policy")
    assert response.headers.get("x-request-id")


def test_cors_headers_are_restricted():
    response = client.options(
        "/health",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code in (200, 400, 403)
    if "access-control-allow-origin" in response.headers:
        assert response.headers["access-control-allow-origin"] in {"http://localhost:3000", "https://localhost:3000"}
        assert "https://evil.example" not in response.headers["access-control-allow-origin"]
