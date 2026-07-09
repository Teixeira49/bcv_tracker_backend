from pydantic import BaseModel, Field
from typing import Optional, List, Any, Generic, TypeVar

T = TypeVar("T")

class BaseResponse(BaseModel, Generic[T]):
    status: str = Field(..., description="Estado de la respuesta (ej. Success)")
    message: str = Field(..., description="Detalle o mensaje de la operación")
    data: Optional[T] = Field(None, description="Datos de la respuesta")

class CurrencySchema(BaseModel):
    id: Optional[int] = None
    code: str
    name: str
    platform: str
    value: float
    change: float
    createDate: Optional[str] = None
    updateDate: Optional[str] = None
    platform_img: Optional[str] = None

class BcvResponseData(BaseModel):
    date: Optional[str] = None
    currencies: List[CurrencySchema]

class AllCurrenciesResponseData(BaseModel):
    bcv: List[CurrencySchema]
    yadio: List[CurrencySchema]
    binance: List[CurrencySchema]
    bybit: List[CurrencySchema]
    exchange_monitor: List[CurrencySchema]

class UpdateCurrenciesResponseData(BaseModel):
    message: str
    updated_currencies: Optional[int] = Field(None, alias="updated_count")

    class Config:
        populate_by_name = True

class ErrorResponse(BaseModel):
    status: str = Field(..., description="Estado del error (ej. Error)")
    message: str = Field(..., description="Mensaje detallado del error")
