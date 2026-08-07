from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import List

from api.core.config.config import Config as c
from ..models.bd_currency import Base, Currency, PlatformDate
from api.utils.constants.constants import Constants
from api.utils.helpers.helper import Helper

# Lee la URL de la base de datos desde las variables de entorno.
# El archivo .env que mostraste contiene esta variable. Vercel la inyectará automáticamente.
DATABASE_URL = c.DATABASE_URL

if not DATABASE_URL:
    raise ValueError("No DATABASE_URL environment variable set")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Crea las tablas si no existen.

    Se invoca UNA sola vez en el arranque de la app (evento ``lifespan`` de
    ``api/main.py``), no por request. El esquema versionado lo gobierna Alembic
    (``alembic upgrade head``); este ``create_all`` es una garantía idempotente
    de que las tablas existan en entornos efímeros (serverless / cold start).
    """
    Base.metadata.create_all(bind=engine)

def _variant_of(currency: Currency) -> str:
    """Variante efectiva de una moneda entrante, con el centinela aplicado.

    El default ``'na'`` de la columna solo se materializa al insertar, así que una
    ``Currency`` construida sin variante la trae en ``None`` mientras vive en
    memoria. Sin normalizar, esa moneda buscaría la clave ``(code, platform, None)``
    y no encontraría su fila —guardada con ``'na'``—, intentaría insertar y
    chocaría contra el UNIQUE. Se normaliza en un solo punto para que la búsqueda
    y la inserción usen exactamente el mismo valor.
    """
    return currency.variant or Constants.VARIANT_NA

def save_currencies_to_db(currencies: List[Currency]):
    """Persiste (upsert) una lista de monedas y calcula su variación (ROC).

    Por cada moneda busca el registro existente con la misma clave de negocio
    ``(code, platform, variant)``: si existe, lo actualiza y calcula el cambio
    porcentual respecto al valor previo; si no, inserta un registro nuevo con
    ``change = 0.0``. Toda la operación es transaccional (``commit`` al final,
    ``rollback`` ante error).

    La variante forma parte de la clave desde #73. Antes la clave era solo
    ``(code, platform)``, y como las fuentes que publican varias series por
    moneda (compra/venta en los P2P, oficial/paralelo en DolarAPI) las envían en
    el mismo lote, la segunda escritura pisaba a la primera: quedaba una sola
    fila con el último valor y un ROC que era en realidad el spread entre series.

    :param currencies: monedas a guardar o actualizar.
    """
    session = SessionLocal()
    try:
        now = Helper().getZoneTime()

        # Precarga en UNA sola consulta las filas existentes de los (code, platform)
        # del lote, en lugar de un SELECT por moneda (patrón N+1). El número de
        # queries de lectura es constante e independiente de la cantidad de monedas.
        # La sesión usa autoflush=False, así que —igual que antes— ninguna
        # inserción/actualización del lote es visible dentro del propio bucle.
        codes = {cur.code for cur in currencies}
        platforms = {cur.platform for cur in currencies}
        existing_by_key = {}
        if codes and platforms:
            existing_rows = (
                session.query(Currency)
                .filter(Currency.code.in_(codes), Currency.platform.in_(platforms))
                .order_by(Currency.id.asc())
                .all()
            )
            for row in existing_rows:
                key = (row.code, row.platform, row.variant)
                # La clave incluye la variante, así que cada serie (compra, venta,
                # oficial, ...) mapea a su propia fila y ya no compiten por una
                # sola. El UNIQUE de la tabla hace que no pueda haber más de una
                # fila por clave; el `if` se conserva como red defensiva y, si
                # aun así hubiera duplicados, gana la de `id` más bajo.
                if key not in existing_by_key:
                    existing_by_key[key] = row

        for cur in currencies:
            # Registro existente con la misma clave de negocio (precargado).
            existing_row = existing_by_key.get((cur.code, cur.platform, _variant_of(cur)))

            # actualizar o crear el registro "todayData == True"
            if existing_row:
                # Si existe un registro con el mismo código y todayData, actualízalo
                # Calculamos el indicador de variacion % (ROC) con el helper único.
                cur.change = Helper().rate_of_change(existing_row.value, cur.value)

                existing_row.name = cur.name
                existing_row.value = cur.value
                existing_row.change = cur.change
                existing_row.updateDate = now
            # actualizar o crear el registro "todayData == False"
            else:
                # Si no existe un registro con el mismo código y todayData, crea uno nuevo
                cur.change = 0.0
                new_currency = Currency(
                    code=cur.code,
                    name=cur.name,
                    platform=cur.platform,
                    variant=_variant_of(cur),
                    value=cur.value,
                    change=cur.change,
                    createDate=now,
                    updateDate=now,
                )
                session.add(new_currency)

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def save_platform_date(platform: str, date_value: str):
    """Guarda (upsert) la fecha de última actualización de una plataforma.

    :param platform: nombre de la plataforma (p. ej. ``"Banco Central de Venezuela"``).
    :param date_value: fecha reportada por la fuente, como texto.
    """
    session = SessionLocal()
    try:
        now = Helper().getZoneTime()
        existing_row = session.query(PlatformDate).filter(PlatformDate.platform == platform).first()

        if existing_row:
            existing_row.date = date_value
            existing_row.updateDate = now
        else:
            new_entry = PlatformDate(
                platform=platform,
                date=date_value,
                createDate=now,
                updateDate=now
            )
            session.add(new_entry)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def get_platform_date(platform: str) -> str:
    """Devuelve la fecha almacenada de una plataforma, o ``None`` si no existe.

    :param platform: nombre de la plataforma a consultar.
    :return: la fecha guardada como texto, o ``None`` si no hay registro o
        falla la lectura.
    """
    session = SessionLocal()
    try:
        row = session.query(PlatformDate).filter(PlatformDate.platform == platform).first()
        return row.date if row else None
    except Exception:
        return None
    finally:
        session.close()