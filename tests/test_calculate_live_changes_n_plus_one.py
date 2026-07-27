"""Issue #27: eliminar el N+1 en ``calculate_live_changes``.

Antes, ``calculate_live_changes`` ejecutaba **una consulta por moneda** dentro
del bucle (patrón N+1) para leer el valor previo y calcular el ROC. Ahora
precarga todos los valores previos en **una sola** consulta ``IN`` sobre el par
``(code, platform)``.

Estos tests fijan el contrato:

- El número de consultas SELECT es **constante (1)** e independiente de la
  cantidad de monedas.
- El ROC calculado por moneda es correcto (valor previo de su ``(code,
  platform)``) y degrada a ``0.0`` cuando no hay valor previo en la BD.
"""
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.models.bd_currency import Base, Currency
from api.services.dollar_services import DollarService


@pytest.fixture
def seeded_session_factory():
    """SessionLocal ligado a una BD SQLite en memoria con valores previos.

    Usa ``StaticPool`` + ``check_same_thread=False`` para que la MISMA base en
    memoria sea visible desde el hilo de ``run_in_executor`` donde corre la
    consulta (sin esto, cada conexión SQLite ``:memory:`` sería una BD vacía).
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    seed = factory()
    try:
        # Valores previos almacenados (base del ROC).
        seed.add_all([
            Currency(code="USD", platform="Banco Central de Venezuela", value=100.0),
            Currency(code="EUR", platform="Banco Central de Venezuela", value=200.0),
            Currency(code="USDT", platform="Binance", value=40.0),
        ])
        seed.commit()
    finally:
        seed.close()

    return engine, factory


def _count_selects(engine):
    """Cuenta las sentencias SELECT ejecutadas contra el engine."""
    counter = {"selects": 0}

    @event.listens_for(engine, "before_cursor_execute")
    def _before(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            counter["selects"] += 1

    return counter


@pytest.mark.asyncio
async def test_calculate_live_changes_issues_single_query(seeded_session_factory, monkeypatch):
    """Con N monedas se ejecuta una sola consulta (no N)."""
    engine, factory = seeded_session_factory
    monkeypatch.setattr("api.services.dollar_services.SessionLocal", factory)

    service = DollarService()
    live = [
        service.createCurrency("USD", "Dolar", 110.0, "Banco Central de Venezuela"),
        service.createCurrency("EUR", "Euro", 200.0, "Banco Central de Venezuela"),
        service.createCurrency("USDT", "Tether", 50.0, "Binance"),
    ]

    counter = _count_selects(engine)
    await service.calculate_live_changes(live)

    assert counter["selects"] == 1


@pytest.mark.asyncio
async def test_calculate_live_changes_computes_roc_per_currency(seeded_session_factory, monkeypatch):
    """El ROC por moneda usa su valor previo; sin base previa degrada a 0.0."""
    engine, factory = seeded_session_factory
    monkeypatch.setattr("api.services.dollar_services.SessionLocal", factory)

    service = DollarService()
    live = [
        service.createCurrency("USD", "Dolar", 110.0, "Banco Central de Venezuela"),   # 100 -> 110 = +10%
        service.createCurrency("EUR", "Euro", 150.0, "Banco Central de Venezuela"),    # 200 -> 150 = -25%
        service.createCurrency("USDT", "Tether", 50.0, "Binance"),                     # 40 -> 50 = +25%
        service.createCurrency("BTC", "Bitcoin", 999.0, "Yadio.io"),                   # sin previo -> 0.0
    ]

    result = await service.calculate_live_changes(live)
    changes = {(c.code, c.platform): c.change for c in result}

    assert changes[("USD", "Banco Central de Venezuela")] == pytest.approx(10.0)
    assert changes[("EUR", "Banco Central de Venezuela")] == pytest.approx(-25.0)
    assert changes[("USDT", "Binance")] == pytest.approx(25.0)
    assert changes[("BTC", "Yadio.io")] == 0.0
