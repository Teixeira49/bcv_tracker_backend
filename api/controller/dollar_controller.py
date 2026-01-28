from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
import asyncio
import httpx

from api.core.response.response_wrapper import api_response
from api.services.dollar_services import DollarService

router = APIRouter(prefix="/api/venezuela", tags=["Venezuela"])

dollar_service = DollarService() # Crea una instancia de DollarService

class FilterParams:
    actualRate: bool = Field(True)

# ============================================================================================
#  >> Obtener informacion de dolares inmediata de distintos mercados
# --------------------------------------------------------------------------------------------

@router.get('')
async def get_all_currencies(averaged: bool = Query(False)):
    try:
        # Iniciamos las tareas de BCV y Yadio
        bcv_task = dollar_service.getCurrenciesByBCV()
        yadio_task = dollar_service.getCurrenciesByYadio()
        
        async with httpx.AsyncClient() as client:
            # Preparamos las 4 tareas de Binance (necesarias para ambos casos)
            task_usdt_buy = dollar_service.getCurrenciesByBinance(client, "USDT", "VES", "Buy")
            task_usdc_buy = dollar_service.getCurrenciesByBinance(client, "USDC", "VES", "Buy")
            task_usdt_sell = dollar_service.getCurrenciesByBinance(client, "USDT", "VES", "Sell")
            task_usdc_sell = dollar_service.getCurrenciesByBinance(client, "USDC", "VES", "Sell")

            # Ejecutamos TODO en paralelo (6 peticiones concurrentes)
            bcv_res, yadio_res, usdt_buy, usdc_buy, usdt_sell, usdc_sell = await asyncio.gather(
                bcv_task, yadio_task, task_usdt_buy, task_usdc_buy, task_usdt_sell, task_usdc_sell
            )

        # Procesamos la lógica de Binance según el parámetro
        if averaged:
            binance_data = [
                dollar_service.serialize_with_image(dollar_service.createBinanceCurrency("USDT", "Tether", (usdt_buy.value + usdt_sell.value) / 2)),
                dollar_service.serialize_with_image(dollar_service.createBinanceCurrency("USDC", "USD Coin", (usdc_buy.value + usdc_sell.value) / 2))
            ]
        else:
            binance_data = [
                dollar_service.serialize_with_image(usdt_buy),
                dollar_service.serialize_with_image(usdc_buy),
                dollar_service.serialize_with_image(usdt_sell),
                dollar_service.serialize_with_image(usdc_sell)
            ]

        return api_response({
            "bcv": bcv_res['currencies'],
            "yadio": yadio_res,
            "binance": binance_data
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bcv")
async def get_bcv_currencies():
    try:
        exchange_rate = await dollar_service.getCurrenciesByBCV()
        return api_response(exchange_rate)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/bcv/dollar")
async def get_bcv_dollar():
    try:
        exchange_rate = await dollar_service.getDollarValueByBCV()
        return api_response(exchange_rate)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/yadio")
async def get_yadio_currencies():
    try:
        exchange_rate = await dollar_service.getCurrenciesByYadio()
        return api_response(exchange_rate)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/yadio/dollar")
async def get_yadio_dollar():
    try:
        exchange_rate = await dollar_service.getDollarByYadio()
        return api_response(exchange_rate)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/binance")
async def get_binance_currencies():
    try:
        async with httpx.AsyncClient() as client:
            task_usdt_buy = dollar_service.getCurrenciesByBinance(client, "USDT", "VES", "Buy")
            task_usdc_buy = dollar_service.getCurrenciesByBinance(client, "USDC", "VES", "Buy")
            task_usdt_sell = dollar_service.getCurrenciesByBinance(client, "USDT", "VES", "Sell")
            task_usdc_sell = dollar_service.getCurrenciesByBinance(client, "USDC", "VES", "Sell")

            usdt_buy, usdc_buy, usdt_sell, usdc_sell = await asyncio.gather(
                task_usdt_buy,
                task_usdc_buy,
                task_usdt_sell,
                task_usdc_sell
            )

        return api_response([
            dollar_service.serialize_with_image(usdt_buy),
            dollar_service.serialize_with_image(usdc_buy),
            dollar_service.serialize_with_image(usdt_sell),
            dollar_service.serialize_with_image(usdc_sell)
        ])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/binance/averaged")
async def get_binance_averaged():
    try:
        async with httpx.AsyncClient() as client:
            # Ejecutamos las 4 solicitudes en paralelo
            task_usdt_buy = dollar_service.getCurrenciesByBinance(client, "USDT", "VES", "Buy")
            task_usdc_buy = dollar_service.getCurrenciesByBinance(client, "USDC", "VES", "Buy")
            task_usdt_sell = dollar_service.getCurrenciesByBinance(client, "USDT", "VES", "Sell")
            task_usdc_sell = dollar_service.getCurrenciesByBinance(client, "USDC", "VES", "Sell")

            usdt_buy, usdc_buy, usdt_sell, usdc_sell = await asyncio.gather(
                task_usdt_buy,
                task_usdc_buy,
                task_usdt_sell,
                task_usdc_sell
            )

        # Calculamos los promedios de compra y venta
        avg_tether = (usdt_buy.value + usdt_sell.value) / 2
        avg_usdc = (usdc_buy.value + usdc_sell.value) / 2

        # Creamos las nuevas entidades promediadas con nombres limpios
        tether_averaged = dollar_service.createBinanceCurrency("USDT", "Tether", avg_tether)
        usdc_averaged = dollar_service.createBinanceCurrency("USDC", "USD Coin", avg_usdc)

        return api_response([
            dollar_service.serialize_with_image(tether_averaged),
            dollar_service.serialize_with_image(usdc_averaged)
        ])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# ============================================================================================
#  >> Usar informacion de memoria sobre los mercados
# --------------------------------------------------------------------------------------------

@router.put(
    "/update-latest-exchange-rate", 
    tags=["Venezuela | Save Data"], 
    summary="Actualizar base de datos con tasas del BCV"
)
async def get_latest_exchange_rate():
    try:
        exchange_rate = await dollar_service.getCurrenciesByBCV() # Llama al método desde la instancia
        return {"exchange_rate": exchange_rate}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/actual-exchange-rate")
async def get_saved_currencies(today_data: Optional[bool] = Query(None, alias="today-data")):
    try:
        currencies = await dollar_service.getSavedCurrencies(today_data) # Llama al método desde la instancia
        return {"exchange_rate": currencies}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))