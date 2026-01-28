from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from typing import List

from api.core.config.config import Config as c
from ..models.bd_currency import Base, Currency
from api.utils.helpers.helper import Helper

# Lee la URL de la base de datos desde las variables de entorno.
# El archivo .env que mostraste contiene esta variable. Vercel la inyectará automáticamente.
DATABASE_URL = c.DATABASE_URL

if not DATABASE_URL:
    raise ValueError("No DATABASE_URL environment variable set")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Crear tablas si no existen."""
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

    init_db()
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
                existing_row.name = cur.name
                existing_row.value = cur.value
                existing_row.updateDate = now
            # actualizar o crear el registro "todayData == False"
            else:
                # Si no existe un registro con el mismo código y todayData, crea uno nuevo
                new_currency = Currency(
                    code=cur.code,
                    name=cur.name,
                    platform=cur.platform,
                    platformLinkImage=cur.platformLinkImage,
                    symbolLinkImage=cur.symbolLinkImage,
                    value=cur.value,
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