from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, UniqueConstraint, func
from sqlalchemy.ext.declarative import declarative_base

from api.utils.constants.constants import Constants as c

Base = declarative_base()

class Currency(Base):
    __tablename__ = "currencies"

    # La identidad de negocio de una cotización es (code, platform, variant): una
    # misma moneda de una misma plataforma puede publicar varias series a la vez
    # (compra/venta en los P2P, oficial/paralelo en DolarAPI). El UNIQUE lo hace
    # cumplir en la BD, para que el upsert del servicio no pueda volver a generar
    # filas gemelas que luego se quedan huérfanas (issue #73).
    __table_args__ = (
        UniqueConstraint("code", "platform", "variant", name="uq_currencies_code_platform_variant"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False, index=True)
    name = Column(String)
    platform = Column(String)
    # Serie de la cotización dentro de (code, platform). NOT NULL con centinela
    # 'na': un NULL no serviría, porque los NULL cuentan como distintos entre sí
    # en un índice único (tanto en PostgreSQL como en SQLite) y el UNIQUE de
    # arriba dejaría de proteger a las fuentes de una sola serie.
    variant = Column(String, nullable=False, server_default=c.VARIANT_NA, default=c.VARIANT_NA)
    value = Column(Float)
    change = Column(Float, default=0.0)
    createDate = Column(DateTime, default=func.now(), nullable=False)
    updateDate = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<Currency(code={self.code}, variant={self.variant}, value={self.value})>"

    def to_dict(self):
        return {
            "code": self.code,
            "name": self.name,
            "platform": self.platform,
            "variant": self.variant,
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