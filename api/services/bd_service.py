from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from typing import List

from api.core.config.config import Config as c
from ..models.bd_currency import Base, Currency, PlatformDate
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

def reset_db():
    """Comprueba si la tabla existe y la elimina para reiniciarla."""
    inspector = inspect(engine)
    # Verificamos si la tabla 'currencies' existe
    if inspector.has_table(Currency.__tablename__):
        print(f"Reiniciando tabla: {Currency.__tablename__}")
        # Eliminamos solo la tabla específica
        Currency.__table__.drop(engine)
    
    # Volvemos a crear las tablas
    init_db()

def save_currencies_to_db(currencies: List[Currency]):
    """Persiste (upsert) una lista de monedas y calcula su variación (ROC).

    Por cada moneda busca el registro existente con el mismo ``(code, platform)``:
    si existe, lo actualiza y calcula el cambio porcentual respecto al valor
    previo; si no, inserta un registro nuevo con ``change = 0.0``. Toda la
    operación es transaccional (``commit`` al final, ``rollback`` ante error).

    :param currencies: monedas a guardar o actualizar.
    """
    session = SessionLocal()
    try:
        now = Helper().getZoneTime()
        for cur in currencies:
            # Intenta obtener el registro existente con el mismo código y valor de todayData
            existing_row = session.query(Currency).filter(
                Currency.code == cur.code,
                Currency.platform == cur.platform,
            ).first()

            # actualizar o crear el registro "todayData == True"
            if existing_row:
                # Si existe un registro con el mismo código y todayData, actualízalo
                # Calculamos el indicador de variacion % (ROC)
                previous_value = existing_row.value
                if previous_value and previous_value != 0:
                    cur.change = ((cur.value - previous_value) / previous_value) * 100 # Cambiar a un helper
                else:
                    cur.change = 0.0

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