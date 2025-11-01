from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Currency(Base):
    __tablename__ = "currencies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False, index=True)
    name = Column(String)
    linkImage = Column(String)
    exchangeRate = Column(Float)
    createDate = Column(DateTime, default=func.now(), nullable=False)
    updateDate = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    todayData = Column(Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<Currency(code={self.code}, exchangeRate={self.exchangeRate})>"