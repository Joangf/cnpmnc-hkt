"""Fixture dùng chung cho mọi test. Agent test-automator chỉ dùng các fixture ở đây."""
import os

import httpx
import pytest
from pathlib import Path

# Nạp .env ở gốc repo (nếu có) để test và agent dùng chung một cấu hình
_env = Path(__file__).resolve().parent.parent / ".env"
if _env.exists():
    for _line in _env.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")
WEB_BASE_URL = os.getenv("WEB_BASE_URL", "http://localhost:8080")
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")  # backend phải chạy với chính DB này
KEEP_TABLES = {t.strip() for t in os.getenv("KEEP_TABLES", "alembic_version").split(",") if t.strip()}


@pytest.fixture(scope="session")
def api():
    """Client gọi API thật của backend."""
    with httpx.Client(base_url=API_BASE_URL, timeout=10) as client:
        yield client


@pytest.fixture(scope="session")
def web_base_url():
    return WEB_BASE_URL


@pytest.fixture(autouse=True)
def clean_db():
    """Xóa dữ liệu TRƯỚC mỗi test (giữ lại bảng trong KEEP_TABLES, ví dụ bảng seed khoa/triệu chứng).
    Không đặt TEST_DATABASE_URL thì bỏ qua — test phải tự tạo dữ liệu không trùng (dùng uuid)."""
    if TEST_DATABASE_URL:
        import psycopg

        with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as conn:
            rows = conn.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            ).fetchall()
            tables = [r[0] for r in rows if r[0] not in KEEP_TABLES]
            if tables:
                conn.execute(
                    "TRUNCATE " + ", ".join(f'"{t}"' for t in tables) + " RESTART IDENTITY CASCADE"
                )
    yield
