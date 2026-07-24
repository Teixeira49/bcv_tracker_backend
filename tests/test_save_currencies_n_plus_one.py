"""Issue #48: eliminar el N+1 en save_currencies_to_db.

Antes, ``save_currencies_to_db`` ejecutaba **una consulta de existencia por
moneda** dentro del bucle (patrón N+1). Ahora precarga todas las filas
existentes de los ``(code, platform)`` del lote en **una sola** consulta ``IN``.

Estos tests fijan el contrato:

- El número de consultas SELECT es **constante (1)** e independiente de la
  cantidad de monedas.
- El upsert se mantiene: se actualizan las filas existentes (con ROC vs su valor
  previo) y se insertan las nuevas (con ``change = 0.0``).
"""
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.models.bd_currency import Base, Currency
from api.utils.constants.constants import Constants as c
import api.services.bd_service as bd_service


@pytest.fixture
def in_memory_db(monkeypatch):
    """SessionLocal ligado a una BD SQLite en memoria compartida."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    monkeypatch.setattr(bd_service, "SessionLocal", factory)
    return engine, factory


def _make(code, name, platform, value):
    return Currency(code=code, name=name, platform=platform, value=value)


def _count_selects(engine):
    counter = {"selects": 0}

    @event.listens_for(engine, "before_cursor_execute")
    def _before(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            counter["selects"] += 1

    return counter


def test_single_select_regardless_of_count(in_memory_db):
    """Con N monedas se ejecuta una sola consulta de existencia (no N)."""
    engine, factory = in_memory_db

    # Semilla: una fila existente para USD/BCV.
    seed = factory()
    seed.add(_make("USD", "Dolar", c.BCV_NAME, 100.0))
    seed.commit()
    seed.close()

    counter = _count_selects(engine)
    bd_service.save_currencies_to_db([
        _make("USD", "Dolar", c.BCV_NAME, 110.0),   # update
        _make("EUR", "Euro", c.BCV_NAME, 50.0),      # insert
        _make("CNY", "Yuan", c.BCV_NAME, 7.0),       # insert
    ])

    assert counter["selects"] == 1


def test_upsert_updates_and_inserts_with_roc(in_memory_db):
    """Actualiza la fila existente (ROC vs valor previo) e inserta las nuevas."""
    engine, factory = in_memory_db

    seed = factory()
    seed.add(_make("USD", "Dolar", c.BCV_NAME, 100.0))
    seed.commit()
    seed.close()

    bd_service.save_currencies_to_db([
        _make("USD", "Dolar", c.BCV_NAME, 110.0),   # 100 -> 110 = +10%
        _make("EUR", "Euro", c.BCV_NAME, 50.0),      # nuevo -> change 0.0
    ])

    check = factory()
    try:
        usd = check.query(Currency).filter_by(code="USD", platform=c.BCV_NAME).one()
        eur = check.query(Currency).filter_by(code="EUR", platform=c.BCV_NAME).one()
        assert usd.value == 110.0
        assert usd.change == pytest.approx(10.0)
        assert eur.value == 50.0
        assert eur.change == 0.0
    finally:
        check.close()
