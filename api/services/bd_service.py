from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from typing import List

from ..models.bd_currency import Base, Currency
from api.utils.helper import Helper

# Lee la URL de la base de datos desde las variables de entorno.
# El archivo .env que mostraste contiene esta variable. Vercel la inyectará automáticamente.
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("No DATABASE_URL environment variable set")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Crear tablas si no existen."""
    Base.metadata.create_all(bind=engine)

def save_currencies_to_db(currencies: List[Currency]):

    init_db()
    session = SessionLocal()
    try:
        now = Helper.getZoneTime()
        for cur in currencies:
            # Intenta obtener el registro existente con el mismo código y valor de todayData
            existing_row = session.query(Currency).filter(
                Currency.code == cur.code,
                Currency.todayData == cur.todayData
            ).first()

            # actualizar o crear el registro "todayData == True"
            if existing_row:
                # Si existe un registro con el mismo código y todayData, actualízalo
                existing_row.name = cur.name
                existing_row.linkImage = cur.linkImage
                existing_row.exchangeRate = cur.exchangeRate
                existing_row.updateDate = now
            # actualizar o crear el registro "todayData == False"
            else:
                # Si no existe un registro con el mismo código y todayData, crea uno nuevo
                new_currency = Currency(
                    code=cur.code,
                    name=cur.name,
                    linkImage=cur.linkImage,
                    exchangeRate=cur.exchangeRate,
                    createDate=now,
                    updateDate=now,
                    todayData=cur.todayData
                )
                session.add(new_currency)

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()