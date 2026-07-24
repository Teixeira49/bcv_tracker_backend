"""Issue #15: unificar el acceso a BD para no bloquear el event loop.

``getSavedCurrencies`` ejecutaba ``session.query(...)`` síncrono directamente
dentro del ``async def``, bloqueando el event loop de asyncio y quedando
inconsistente con el resto de accesos a BD del service
(``save_currencies_to_db_async``, ``save_platform_date_async``,
``calculate_live_changes``), que sí delegan el trabajo bloqueante a un hilo con
``run_in_executor``.

Estos tests fijan el contrato esperado tras el refactor:

- La lectura bloqueante corre en un hilo (``run_in_executor``): mientras dura,
  el event loop sigue vivo y otras corrutinas avanzan (no se bloquea).
- La lógica funcional (consulta, filtrado por plataforma, serialización con
  ``id`` y logo, degradación a ``[]`` ante error) se preserva en el helper
  síncrono ``_fetch_saved_currencies``.
"""
import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from api.services.dollar_services import DollarService
from api.utils.constants.constants import Constants as c


def _make_currency(service, code, platform, value, cid):
    """Construye un Currency (vía la fábrica del service) con un id asignado."""
    cur = service.createCurrency(code, "Dolar", value, platform)
    cur.id = cid
    return cur


class _FakeQuery:
    """Query encadenable mínima que imita ``session.query(...)`` de SQLAlchemy."""

    def __init__(self, rows):
        self._rows = rows

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, rows):
        self._rows = rows
        self.closed = False

    def query(self, *args, **kwargs):
        return _FakeQuery(self._rows)

    def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_getSavedCurrencies_no_bloquea_el_event_loop(monkeypatch):
    """La lectura de BD corre en un hilo: el event loop no se bloquea."""
    service = DollarService()

    # Simula la consulta SQLAlchemy síncrona: duerme el HILO (no ``asyncio.sleep``).
    # Si esto corriera en el event loop, el ticker de abajo no avanzaría.
    def _blocking_fetch(platforms=None):
        time.sleep(0.3)
        return [{"code": "USD"}]

    monkeypatch.setattr(service, "_fetch_saved_currencies", _blocking_fetch)

    ticks = 0

    async def _ticker():
        nonlocal ticks
        while True:
            ticks += 1
            await asyncio.sleep(0.01)

    ticker_task = asyncio.create_task(_ticker())
    result = await service.getSavedCurrencies()
    ticker_task.cancel()

    assert result == [{"code": "USD"}]
    # Con el read en un hilo (run_in_executor), el loop siguió vivo ~0.3s y el
    # ticker (cada 0.01s) avanzó muchas veces. Bloqueado, ticks sería ~0.
    assert ticks > 5


@pytest.mark.asyncio
async def test_getSavedCurrencies_serializa_filas_con_id_y_logo(monkeypatch):
    """El resultado incluye id + platform_img y respeta el orden (id desc)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from api.models.bd_currency import Base, Currency

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    seed = factory()
    seed.add(Currency(code="EUR", name="Euro", platform=c.BCV_NAME, value=110.0))   # id 1
    seed.add(Currency(code="USD", name="Dolar", platform=c.BCV_NAME, value=100.0))  # id 2
    seed.commit()
    seed.close()
    monkeypatch.setattr("api.services.dollar_services.SessionLocal", factory)

    service = DollarService()
    result = await service.getSavedCurrencies(platforms=[c.BCV_NAME])

    # Última por (code, platform), ordenado por id desc.
    assert [r["id"] for r in result] == [2, 1]
    assert [r["code"] for r in result] == ["USD", "EUR"]
    assert all(r["platform_img"] == c.BCV_LOGO_URL for r in result)


@pytest.mark.asyncio
async def test_getSavedCurrencies_devuelve_lista_vacia_ante_error(monkeypatch):
    """Un fallo de lectura degrada a ``[]`` sin propagar la excepción."""
    service = DollarService()

    def _boom():
        session = MagicMock()
        session.query.side_effect = RuntimeError("db down")
        return session

    monkeypatch.setattr("api.services.dollar_services.SessionLocal", _boom)

    result = await service.getSavedCurrencies()

    assert result == []
