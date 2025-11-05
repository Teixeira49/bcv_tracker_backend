from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from api.services.dollar_services import DollarService

router = APIRouter(prefix="/api")

class FilterParams:
    actualRate: bool = Field(True)
    
@router.put("/update-latest-exchange-rate")
async def get_latest_exchange_rate():
    try:
        exchange_rate = await DollarService.getCurrenciesByBCV()
        return {"exchange_rate": exchange_rate}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/actual-exchange-rate")
async def get_saved_currencies(today_data: Optional[bool] = Query(None, alias="today-data")):
    try:
        currencies = await DollarService.getSavedCurrencies(today_data)
        return {"exchange_rate": currencies}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))