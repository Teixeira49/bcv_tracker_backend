from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Currency(Base):
    __tablename__ = "currencies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False, index=True)
    name = Column(String)
    platform = Column(String)
    value = Column(Float)
    change = Column(Float, default=0.0)
    createDate = Column(DateTime, default=func.now(), nullable=False)
    updateDate = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<Currency(code={self.code}, value={self.value})>"
    
    def to_dict(self):
        return {
            "code": self.code,
            "name": self.name,
            "platform": self.platform,
            "value": self.value,
            "change": self.change,
            "createDate": self.createDate.isoformat() if self.createDate else None,
            "updateDate": self.updateDate.isoformat() if self.updateDate else None,
        }

class PlatformDate(Base):
    __tablename__ = "platform_dates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String, unique=True, nullable=False)
    date = Column(String)
    createDate = Column(DateTime, default=func.now(), nullable=False)
    updateDate = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<PlatformDate(platform={self.platform}, date={self.date})>"