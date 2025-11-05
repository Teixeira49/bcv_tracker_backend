from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from typing import List
from datetime import datetime

from ..models.bd_currency import Base, Currency
from ..utils.constants import Constants
from ..models.bcv_currency import BcvCurrency

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
        now = datetime.utcnow()
        for cur in currencies:
            # obtener todos los registros con ese código
            rows = session.query(Currency).filter(Currency.code == cur.code).all()

            row_true = next((r for r in rows if r.todayData), None)
            row_false = next((r for r in rows if not r.todayData), None)

            # actualizar o crear el registro "todayData == True"
            if row_true:
                row_true.name = cur.name
                row_true.linkImage = cur.linkImage
                row_true.exchangeRate = cur.exchangeRate
                row_true.updateDate = now
                row_true.todayData = True
            else:
                new_true = Currency(
                    code=cur.code,
                    name=cur.name,
                    linkImage=cur.linkImage,
                    exchangeRate=cur.exchangeRate,
                    createDate=now,
                    updateDate=now,
                    todayData=True
                )
                session.add(new_true)

            # actualizar o crear el registro "todayData == False"
            if row_false:
                row_false.name = cur.name
                row_false.linkImage = cur.linkImage
                row_false.exchangeRate = cur.exchangeRate
                row_false.updateDate = now
                row_false.todayData = False
            else:
                new_false = Currency(
                    code=cur.code,
                    name=cur.name,
                    linkImage=cur.linkImage,
                    exchangeRate=cur.exchangeRate,
                    createDate=now,
                    updateDate=now,
                    todayData=False
                )
                session.add(new_false)

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()