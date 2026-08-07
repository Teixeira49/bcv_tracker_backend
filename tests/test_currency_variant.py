"""Issue #73: la variante separa las series de una misma moneda.

Antes, el lado de la operación vivía dentro del ``name`` ("Tether-Buy") y la
clave de negocio era solo ``(code, platform)``. Como cada fuente manda todas sus
series en el mismo lote, la segunda escritura pisaba a la primera: quedaba una
sola fila por moneda, con el valor del último lado y un ROC que en realidad era
el spread entre series. Además, la lectura tomaba ``max(id)`` mientras el upsert
escribía en la fila de ``id`` más bajo, así que ante filas gemelas la API servía
justo la que nadie estaba actualizando.

Estos tests fijan el contrato nuevo:

- Cada fuente etiqueta la serie que produce (``buy``/``sell``, ``oficial``/
  ``paralelo``, ``average``, o el centinela ``na``).
- El upsert usa ``(code, platform, variant)``: las series conviven en filas
  propias y cada una calcula su ROC contra su propio valor previo.
- El ``UNIQUE`` impide que vuelvan a nacer filas gemelas.
- La migración ``0002`` reutiliza las gemelas existentes en vez de borrarlas.
"""
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import AsyncMock

import api.services.bd_service as bd_service
from api.models.bd_currency import Base, Currency
from api.services.dollar_services import DollarService
from api.utils.constants.constants import Constants as c


REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def in_memory_db(monkeypatch):
    """``SessionLocal`` ligado a una BD SQLite en memoria compartida.

    Se parchea en los dos módulos que la usan: ``bd_service`` (escritura) y
    ``dollar_services``, que la importa por nombre para sus lecturas.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    monkeypatch.setattr(bd_service, "SessionLocal", factory)
    monkeypatch.setattr("api.services.dollar_services.SessionLocal", factory)
    return engine, factory


# --------------------------------------------------------------------------- #
#  Las fuentes etiquetan su serie
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
@pytest.mark.parametrize("trade_type, expected", [("Buy", c.VARIANT_BUY), ("Sell", c.VARIANT_SELL)])
async def test_binance_etiqueta_el_lado_como_variante(trade_type, expected):
    service = DollarService()
    service.client.post = AsyncMock(return_value={"data": [{"adv": {"price": "800.0"}}]})

    currency = await service.getCurrenciesByBinance(None, asset="USDT", fiat="VES", tradeType=trade_type)

    assert currency.variant == expected


def test_airtm_separa_compra_y_venta_en_variantes():
    service = DollarService()
    payload = {"data": {"ves/usd": {"addValue": 100.0, "withdrawValue": 90.0}}}

    currencies = service._airtm_currencies_from_response(payload)

    # Mismo code, misma plataforma: solo la variante las distingue.
    assert {cur.code for cur in currencies} == {"USD"}
    assert [cur.variant for cur in currencies] == [c.VARIANT_BUY, c.VARIANT_SELL]


def test_dolarapi_usa_la_fuente_como_variante():
    service = DollarService()
    payload = [
        {"moneda": "USD", "fuente": "oficial", "promedio": 700.0},
        {"moneda": "USD", "fuente": "paralelo", "promedio": 850.0},
    ]

    currencies = service._dolarapi_currencies_from_response(payload)

    assert [cur.variant for cur in currencies] == [c.VARIANT_OFICIAL, c.VARIANT_PARALELO]


def test_promedio_es_su_propia_serie():
    """El promedio no es la compra ni la venta: se guarda aparte de ambas."""
    service = DollarService()
    sides = [
        service.createCurrency("USDT", "Tether-Buy", 100.0, c.BINANCE_NAME, variant=c.VARIANT_BUY),
        service.createCurrency("USDT", "Tether-Sell", 200.0, c.BINANCE_NAME, variant=c.VARIANT_SELL),
    ]

    averaged = service.average_by_asset(sides, c.BINANCE_NAME)

    assert [cur.variant for cur in averaged] == [c.VARIANT_AVERAGE]
    assert averaged[0].value == 150.0


def test_fuentes_de_una_sola_serie_usan_el_centinela():
    """BCV/Yadio/Exchange Monitor publican una serie por moneda: variante 'na'."""
    service = DollarService()

    currency = service.createCurrency("EUR", "Euro", 1.0, c.BCV_NAME)

    assert currency.variant == c.VARIANT_NA


# --------------------------------------------------------------------------- #
#  Persistencia: las series conviven
# --------------------------------------------------------------------------- #
def test_compra_y_venta_sobreviven_como_filas_distintas(in_memory_db):
    """Regresión: antes la venta pisaba a la compra dentro del mismo lote."""
    _, factory = in_memory_db
    service = DollarService()

    bd_service.save_currencies_to_db([
        service.createCurrency("USDT", "Tether-Buy", 800.0, c.BINANCE_NAME, variant=c.VARIANT_BUY),
        service.createCurrency("USDT", "Tether-Sell", 820.0, c.BINANCE_NAME, variant=c.VARIANT_SELL),
    ])

    check = factory()
    try:
        rows = check.query(Currency).filter_by(code="USDT", platform=c.BINANCE_NAME).all()
        by_variant = {row.variant: row.value for row in rows}
    finally:
        check.close()

    assert by_variant == {c.VARIANT_BUY: 800.0, c.VARIANT_SELL: 820.0}


def test_cada_serie_calcula_su_roc_contra_si_misma(in_memory_db):
    """El ROC de la compra ya no se calcula contra la venta guardada."""
    _, factory = in_memory_db
    service = DollarService()

    bd_service.save_currencies_to_db([
        service.createCurrency("USDT", "Tether-Buy", 100.0, c.BINANCE_NAME, variant=c.VARIANT_BUY),
        service.createCurrency("USDT", "Tether-Sell", 200.0, c.BINANCE_NAME, variant=c.VARIANT_SELL),
    ])
    bd_service.save_currencies_to_db([
        service.createCurrency("USDT", "Tether-Buy", 110.0, c.BINANCE_NAME, variant=c.VARIANT_BUY),
        service.createCurrency("USDT", "Tether-Sell", 150.0, c.BINANCE_NAME, variant=c.VARIANT_SELL),
    ])

    check = factory()
    try:
        rows = check.query(Currency).filter_by(code="USDT", platform=c.BINANCE_NAME).all()
        by_variant = {row.variant: row for row in rows}
    finally:
        check.close()

    # 100 -> 110 = +10% (no 100 -> 150 ni 200 -> 110).
    assert by_variant[c.VARIANT_BUY].change == pytest.approx(10.0)
    # 200 -> 150 = -25%.
    assert by_variant[c.VARIANT_SELL].change == pytest.approx(-25.0)


def test_moneda_sin_variante_cae_en_el_centinela_y_no_duplica(in_memory_db):
    """Una ``Currency`` construida sin variante actualiza su fila 'na', no inserta otra."""
    _, factory = in_memory_db

    bd_service.save_currencies_to_db([Currency(code="USD", name="Dolar", platform=c.BCV_NAME, value=100.0)])
    bd_service.save_currencies_to_db([Currency(code="USD", name="Dolar", platform=c.BCV_NAME, value=110.0)])

    check = factory()
    try:
        rows = check.query(Currency).filter_by(code="USD", platform=c.BCV_NAME).all()
    finally:
        check.close()

    assert len(rows) == 1
    assert rows[0].variant == c.VARIANT_NA
    assert rows[0].value == 110.0


def test_unique_impide_filas_gemelas(in_memory_db):
    """La BD rechaza una segunda fila con la misma (code, platform, variant)."""
    _, factory = in_memory_db

    session = factory()
    try:
        session.add(Currency(code="USDT", name="Tether-sell", platform=c.BINANCE_NAME,
                             variant=c.VARIANT_SELL, value=800.0))
        session.commit()
        session.add(Currency(code="USDT", name="Tether-sell", platform=c.BINANCE_NAME,
                             variant=c.VARIANT_SELL, value=820.0))
        with pytest.raises(IntegrityError):
            session.commit()
    finally:
        session.rollback()
        session.close()


# --------------------------------------------------------------------------- #
#  Lectura
# --------------------------------------------------------------------------- #
def test_la_lectura_devuelve_todas_las_series(in_memory_db):
    """``bd-todas`` devuelve compra y venta, no una sola de las dos."""
    _, factory = in_memory_db
    service = DollarService()

    bd_service.save_currencies_to_db([
        service.createCurrency("USDT", "Tether-Buy", 800.0, c.BINANCE_NAME, variant=c.VARIANT_BUY),
        service.createCurrency("USDT", "Tether-Sell", 820.0, c.BINANCE_NAME, variant=c.VARIANT_SELL),
    ])

    rows = service._fetch_saved_for_platform(c.BINANCE_NAME)

    assert sorted(row["variant"] for row in rows) == [c.VARIANT_BUY, c.VARIANT_SELL]
    assert sorted(row["value"] for row in rows) == [800.0, 820.0]


@pytest.mark.asyncio
async def test_roc_en_vivo_compara_cada_serie_con_la_suya(in_memory_db):
    """``calculate_live_changes`` cruza por variante, no solo por code+platform."""
    _, _ = in_memory_db
    service = DollarService()

    bd_service.save_currencies_to_db([
        service.createCurrency("USDT", "Tether-Buy", 100.0, c.BINANCE_NAME, variant=c.VARIANT_BUY),
        service.createCurrency("USDT", "Tether-Sell", 200.0, c.BINANCE_NAME, variant=c.VARIANT_SELL),
    ])

    live = await service.calculate_live_changes([
        service.createCurrency("USDT", "Tether-Buy", 110.0, c.BINANCE_NAME, variant=c.VARIANT_BUY),
    ])

    assert live[0].change == pytest.approx(10.0)  # 100 -> 110, no 200 -> 110


# --------------------------------------------------------------------------- #
#  Migración de datos
# --------------------------------------------------------------------------- #
def test_migracion_reutiliza_las_filas_gemelas(tmp_path):
    """La 0002 convierte la gemela huérfana en la serie que faltaba, sin borrar nada.

    Reproduce el estado real de producción: dos filas con el mismo
    ``(code, platform)`` y el mismo nombre (ambas terminaron con el de la serie
    que ganaba la escritura), más una fila de una fuente de serie única.
    """
    db_url = f"sqlite:///{tmp_path / 'variant_backfill.db'}"
    import os
    env = {"DATABASE_URL": db_url, "PATH": os.environ.get("PATH", "")}

    up = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "0001_initial_schema"],
                        cwd=REPO_ROOT, env=env, capture_output=True, text=True)
    assert up.returncode == 0, up.stderr

    engine = create_engine(db_url)
    with engine.begin() as conn:
        for row_id, code, name, platform, value in [
            (1, "USDT", "Tether-sell", c.BINANCE_NAME, 860.0),   # viva
            (2, "USDT", "Tether-sell", c.BINANCE_NAME, 870.0),   # gemela congelada
            (3, "USD", "Paralelo", c.DOLARAPI_NAME, 836.0),      # viva
            (4, "USD", "Paralelo", c.DOLARAPI_NAME, 850.0),      # gemela congelada
            (5, "EUR", "Euro", c.BCV_NAME, 841.0),               # serie única
        ]:
            conn.execute(
                text('INSERT INTO currencies (id, code, name, platform, value, change, "createDate", "updateDate")'
                     " VALUES (:id,:code,:name,:platform,:value,0.0,'2026-07-25','2026-07-25')"),
                {"id": row_id, "code": code, "name": name, "platform": platform, "value": value},
            )

    migrate = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"],
                             cwd=REPO_ROOT, env=env, capture_output=True, text=True)
    assert migrate.returncode == 0, migrate.stderr

    with engine.connect() as conn:
        rows = conn.execute(text("SELECT id, variant, value FROM currencies ORDER BY id")).fetchall()
        total = conn.execute(text("SELECT COUNT(*) FROM currencies")).scalar()
    by_id = {row[0]: (row[1], row[2]) for row in rows}

    assert total == 5, "la migración no debe borrar ninguna fila"
    # La fila viva (id más bajo) conserva la serie que dice su nombre.
    assert by_id[1][0] == c.VARIANT_SELL
    assert by_id[3][0] == c.VARIANT_PARALELO
    # La gemela estrena la serie complementaria, con el valor vigente de su hermana.
    assert by_id[2] == (c.VARIANT_BUY, 860.0)
    assert by_id[4] == (c.VARIANT_OFICIAL, 836.0)
    # La fuente de serie única cae en el centinela.
    assert by_id[5][0] == c.VARIANT_NA
