from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
import asyncio
import httpx

from api.core.response.response_wrapper import api_response
from api.services.dollar_services import DollarService
from api.utils.constants.constants import Constants as c

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
                dollar_service.serialize_with_image(dollar_service.createCurrency("USDT", "Tether", (usdt_buy.value + usdt_sell.value) / 2, c.BINANCE_NAME)),
                dollar_service.serialize_with_image(dollar_service.createCurrency("USDC", "USD Coin", (usdc_buy.value + usdc_sell.value) / 2, c.BINANCE_NAME))
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
        tether_averaged = dollar_service.createCurrency("USDT", "Tether", avg_tether, c.BINANCE_NAME)
        usdc_averaged = dollar_service.createCurrency("USDC", "USD Coin", avg_usdc, c.BINANCE_NAME)

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
    "/update-currencies", 
    tags=["Venezuela | Save Data"], 
    summary="Obtiene y guarda en la BD las tasas de las fuentes seleccionadas"
)
async def update_currencies(
    bcv: bool = Query(False, description="Incluir y guardar tasas del BCV."),
    yadio: bool = Query(False, description="Incluir y guardar tasas de Yadio.io."),
    binance: bool = Query(False, description="Incluir y guardar tasas de Binance P2P.")
):
    """
    Ejecuta el scraping de las fuentes de datos especificadas (bcv, yadio, binance)
    y actualiza los registros correspondientes en la base de datos.
    """
    if not any([bcv, yadio, binance]):
        raise HTTPException(
            status_code=400,
            detail="Debe seleccionar al menos una fuente para actualizar. Use los query params: bcv, yadio, binance."
        )

    tasks = []
    if bcv:
        tasks.append(dollar_service.get_raw_bcv_currencies())
    if yadio:
        tasks.append(dollar_service.get_raw_yadio_currencies())
    if binance:
        tasks.append(dollar_service.get_raw_binance_currencies())
    
    try:
        list_of_currency_lists = await asyncio.gather(*tasks)
        
        all_currencies = [currency for sublist in list_of_currency_lists for currency in sublist]
        
        if not all_currencies:
            return api_response(data={"message": "No se obtuvieron datos de las fuentes seleccionadas.", "updated_currencies": 0})

        result = await dollar_service.save_currencies_to_db_async(all_currencies)
        return api_response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ocurrió un error durante la actualización: {str(e)}")
    
@router.get("/saved-currencies", tags=["Venezuela | Save Data"], )
async def get_saved_currencies(
    bcv: bool = Query(False, description="Incluir tasas guardadas del BCV."),
    yadio: bool = Query(False, description="Incluir tasas guardadas de Yadio.io."),
    binance: bool = Query(False, description="Incluir tasas guardadas de Binance P2P.")
):
    """
    Retorna las últimas tasas de cambio guardadas en la base de datos.
    Se puede filtrar por una o más fuentes de datos.
    Si no se especifica ninguna fuente, se retornarán todas las monedas guardadas.
    """
    try:
        platforms_to_fetch = []
        if bcv:
            platforms_to_fetch.append(c.BCV_NAME)
        if yadio:
            platforms_to_fetch.append(c.YADIO_NAME)
        if binance:
            platforms_to_fetch.append(c.BINANCE_NAME)

        # Si la lista está vacía, el servicio traerá todo.
        result = await dollar_service.getSavedCurrencies(platforms=platforms_to_fetch)
        return api_response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))