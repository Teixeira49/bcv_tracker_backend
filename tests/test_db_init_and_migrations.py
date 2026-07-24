"""Issue #19: init_db al arranque (no por escritura) + Alembic con migraciones reales.

Antes, ``init_db()`` (``create_all``) se llamaba en **cada** operación de
escritura (``save_currencies_to_db``, ``save_platform_date``), algo innecesario
por request; y el README prometía ``alembic upgrade head`` sin que existiera
configuración de Alembic.

Estos tests fijan el nuevo contrato:

- ``init_db()`` se ejecuta **una sola vez** en el arranque (evento ``lifespan``).
- Las funciones de escritura **ya no** invocan ``init_db()``.
- La migración inicial de Alembic refleja **exactamente** el esquema de los
  modelos ORM (``alembic check`` no detecta cambios pendientes).
"""
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

import api.main as main
from api.services import bd_service


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_init_db_runs_once_on_startup():
    """El ``lifespan`` inicializa el esquema exactamente una vez al arrancar."""
    with patch("api.services.bd_service.init_db") as mock_init:
        with TestClient(main.app):  # entra/sale del lifespan (startup + shutdown)
            pass
        assert mock_init.call_count == 1


def test_save_currencies_to_db_does_not_call_init_db():
    """``save_currencies_to_db`` ya no crea el esquema por escritura."""
    with patch("api.services.bd_service.init_db") as mock_init, \
            patch("api.services.bd_service.SessionLocal", return_value=MagicMock()):
        bd_service.save_currencies_to_db([])  # lista vacía: no persiste nada
    mock_init.assert_not_called()


def test_save_platform_date_does_not_call_init_db():
    """``save_platform_date`` ya no crea el esquema por escritura."""
    fake_session = MagicMock()
    fake_session.query.return_value.filter.return_value.first.return_value = None
    with patch("api.services.bd_service.init_db") as mock_init, \
            patch("api.services.bd_service.SessionLocal", return_value=fake_session):
        bd_service.save_platform_date("Banco Central de Venezuela", "2026-07-24")
    mock_init.assert_not_called()


def test_alembic_migration_matches_models(tmp_path):
    """La migración inicial refleja el esquema de los modelos ORM.

    Aplica ``alembic upgrade head`` sobre una BD SQLite temporal y luego
    ``alembic check``: si algún modelo cambiara sin su migración correspondiente,
    ``check`` fallaría (guardrail doc-vs-realidad del esquema).
    """
    db_url = f"sqlite:///{tmp_path / 'migrations_test.db'}"
    env = {"DATABASE_URL": db_url, "PATH": __import__("os").environ.get("PATH", "")}

    upgrade = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True,
    )
    assert upgrade.returncode == 0, upgrade.stderr

    check = subprocess.run(
        [sys.executable, "-m", "alembic", "check"],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True,
    )
    assert check.returncode == 0, check.stderr
    assert "No new upgrade operations detected" in (check.stdout + check.stderr)
