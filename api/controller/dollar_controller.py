from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
import httpx
from typing import Optional, List
from api.models.schemas import BaseResponse, CurrencySchema, BcvResponseData, AllCurrenciesResponseData, UpdateCurrenciesResponseData, ErrorResponse

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

@router.get(
    '',
    summary="Obtiene todas las tasas de cambio de múltiples fuentes en tiempo real",
    description="Realiza peticiones concurrentes a las fuentes del Banco Central de Venezuela (BCV), Yadio.io y Binance P2P para retornar las tasas de cambio vigentes para diversas monedas (USD, EUR, USDT, USDC). Permite promediar los valores de Binance mediante el parámetro `averaged`.",
    response_model=BaseResponse[AllCurrenciesResponseData],
    status_code=status.HTTP_200_OK,
    response_description="Tasas de cambio obtenidas exitosamente",
    responses={
        200: {"model": BaseResponse[AllCurrenciesResponseData], "description": "Tasas de cambio obtenidas exitosamente"},
        408: {"model": ErrorResponse, "description": "Tiempo de espera agotado al consultar las fuentes externas"},
        500: {"model": ErrorResponse, "description": "Error al consultar las fuentes externas"}
    }
)
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

@router.get(
    "/bcv",
    summary="Obtiene todas las tasas oficiales publicadas por el Banco Central de Venezuela (BCV)",
    description="Realiza un scraping del portal oficial del BCV para obtener las tasas de cambio vigentes para el Dólar, Euro, Yuan, Lira y Rublo. Incluye la fecha de vigencia reportada por la institución.",
    response_model=BaseResponse[BcvResponseData],
    status_code=status.HTTP_200_OK,
    response_description="Tasas oficiales del BCV obtenidas exitosamente",
    responses={
        200: {"model": BaseResponse[BcvResponseData], "description": "Tasas oficiales del BCV obtenidas exitosamente"},
        408: {"model": ErrorResponse, "description": "Tiempo de espera agotado al intentar acceder al portal del BCV"},
        500: {"model": ErrorResponse, "description": "Error al realizar scraping del portal del BCV"}
    }
)
async def get_bcv_currencies():
    try:
        exchange_rate = await dollar_service.getCurrenciesByBCV()
        return api_response(exchange_rate)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get(
    "/bcv/with-memory",
    summary="Obtiene las tasas del BCV con opción de recuperación desde la base de datos",
    description="Permite recuperar las últimas tasas del BCV almacenadas en la base de datos o forzar una actualización en vivo mediante el parámetro `update`. Es útil para reducir el tiempo de respuesta y la carga sobre el portal oficial.",
    response_model=BaseResponse[BcvResponseData],
    status_code=status.HTTP_200_OK,
    response_description="Tasas del BCV recuperadas exitosamente",
    responses={
        200: {"model": BaseResponse[BcvResponseData], "description": "Tasas del BCV recuperadas exitosamente"},
        408: {"model": ErrorResponse, "description": "Tiempo de espera agotado al consultar los datos del BCV"},
        500: {"model": ErrorResponse, "description": "Error al recuperar datos de la BD o del portal"}
    }
)
async def get_bcv_with_memory(update: bool = Query(False)):
    try:
        if update:
            return api_response(await dollar_service.getCurrenciesByBCV())
        else:
            return api_response(await dollar_service.get_stored_bcv_data())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/bcv/dollar",
    summary="Obtiene el valor específico del Dólar estadounidense según el BCV",
    description="Filtra y retorna únicamente la tasa de cambio oficial del Dólar (USD) publicada por el Banco Central de Venezuela.",
    response_model=BaseResponse[CurrencySchema],
    status_code=status.HTTP_200_OK,
    response_description="Tasa del dólar BCV obtenida exitosamente",
    responses={
        200: {"model": BaseResponse[CurrencySchema], "description": "Tasa del dólar BCV obtenida exitosamente"},
        408: {"model": ErrorResponse, "description": "Tiempo de espera agotado al consultar el valor del dólar BCV"},
        500: {"model": ErrorResponse, "description": "Error al obtener el valor del dólar"}
    }
)
async def get_bcv_dollar():
    try:
        exchange_rate = await dollar_service.getDollarValueByBCV()
        return api_response(exchange_rate)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/yadio",
    summary="Obtiene las tasas de cambio del mercado paralelo a través de Yadio.io",
    description="Consulta la API de Yadio.io para obtener las tasas de cambio del Dólar paralelo, Euro y Bitcoin en Bolívares (VES).",
    response_model=BaseResponse[List[CurrencySchema]],
    status_code=status.HTTP_200_OK,
    response_description="Tasas de Yadio.io obtenidas exitosamente",
    responses={
        200: {"model": BaseResponse[List[CurrencySchema]], "description": "Tasas de Yadio.io obtenidas exitosamente"},
        408: {"model": ErrorResponse, "description": "Tiempo de espera agotado al consultar el API de Yadio.io"},
        500: {"model": ErrorResponse, "description": "Error al conectar con la API de Yadio.io"}
    }
)
async def get_yadio_currencies():
    try:
        exchange_rate = await dollar_service.getCurrenciesByYadio()
        return api_response(exchange_rate)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get(
    "/yadio/dollar",
    summary="Obtiene el valor específico del Dólar paralelo de Yadio.io",
    description="Consulta y retorna exclusivamente la tasa de cambio del Dólar paralelo (USD/VES) reportada por Yadio.io.",
    response_model=BaseResponse[CurrencySchema],
    status_code=status.HTTP_200_OK,
    response_description="Tasa del dólar paralelo obtenida exitosamente",
    responses={
        200: {"model": BaseResponse[CurrencySchema], "description": "Tasa del dólar paralelo obtenida exitosamente"},
        408: {"model": ErrorResponse, "description": "Tiempo de espera agotado al consultar el dólar en Yadio.io"},
        500: {"model": ErrorResponse, "description": "Error al consultar el dólar en Yadio.io"}
    }
)
async def get_yadio_dollar():
    try:
        exchange_rate = await dollar_service.getDollarByYadio()
        return api_response(exchange_rate)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/binance",
    summary="Obtiene las tasas de USDT y USDC de Binance P2P (Compra/Venta)",
    description="Consulta el mercado P2P de Binance para obtener las tasas de compra y venta de USDT y USDC en Bolívares (VES). Retorna los 4 valores (Compra USDT, Venta USDT, Compra USDC, Venta USDC).",
    response_model=BaseResponse[List[CurrencySchema]],
    status_code=status.HTTP_200_OK,
    response_description="Tasas de Binance P2P obtenidas exitosamente",
    responses={
        200: {"model": BaseResponse[List[CurrencySchema]], "description": "Tasas de Binance P2P obtenidas exitosamente"},
        408: {"model": ErrorResponse, "description": "Tiempo de espera agotado al consultar Binance P2P"},
        500: {"model": ErrorResponse, "description": "Error al consultar la API de Binance P2P"}
    }
)
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

@router.get(
    "/binance/averaged",
    summary="Obtiene el promedio de compra y venta para USDT y USDC en Binance P2P",
    description="Calcula el precio promedio entre las órdenes de compra y venta para USDT y USDC en el mercado P2P de Binance, proporcionando una visión equilibrada del mercado cripto-fiat.",
    response_model=BaseResponse[List[CurrencySchema]],
    status_code=status.HTTP_200_OK,
    response_description="Promedios de Binance P2P obtenidos exitosamente",
    responses={
        200: {"model": BaseResponse[List[CurrencySchema]], "description": "Promedios de Binance P2P obtenidos exitosamente"},
        408: {"model": ErrorResponse, "description": "Tiempo de espera agotado al promediar tasas de Binance"},
        500: {"model": ErrorResponse, "description": "Error al calcular promedios de Binance"}
    }
)
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
    summary="Actualiza y persiste las tasas de cambio en la base de datos",
    description="Sincroniza la base de datos con los valores más recientes de las fuentes seleccionadas (BCV, Yadio, Binance). Ejecuta las tareas en paralelo y guarda tanto las tasas como las fechas de actualización de cada plataforma.",
    response_model=BaseResponse[UpdateCurrenciesResponseData],
    status_code=status.HTTP_200_OK,
    response_description="Base de datos actualizada correctamente",
    responses={
        200: {"model": BaseResponse[UpdateCurrenciesResponseData], "description": "Base de datos actualizada correctamente"},
        400: {"model": ErrorResponse, "description": "No se seleccionó ninguna fuente de datos"},
        408: {"model": ErrorResponse, "description": "Tiempo de espera agotado durante la actualización masiva"},
        500: {"model": ErrorResponse, "description": "Error durante el proceso de actualización y guardado"}
    }
)
async def update_currencies(
    bcv: bool = Query(True, description="Incluir y guardar tasas del BCV."),
    yadio: bool = Query(True, description="Incluir y guardar tasas de Yadio.io."),
    binance: bool = Query(True, description="Incluir y guardar tasas de Binance P2P.")
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
        results = await asyncio.gather(*tasks)
        
        all_currencies = []
        result_idx = 0

        if bcv:
            bcv_res = results[result_idx]
            result_idx += 1
            if isinstance(bcv_res, dict):
                all_currencies.extend(bcv_res.get("currencies", []))
                if bcv_res.get("date"):
                    await dollar_service.save_platform_date_async(c.BCV_NAME, bcv_res["date"])
            elif isinstance(bcv_res, list):
                all_currencies.extend(bcv_res)
        
        if yadio:
            all_currencies.extend(results[result_idx])
            result_idx += 1
            
        if binance:
            all_currencies.extend(results[result_idx])
            result_idx += 1
        
        if not all_currencies:
            return api_response(data={"message": "No se obtuvieron datos de las fuentes seleccionadas.", "updated_currencies": 0})

        result = await dollar_service.save_currencies_to_db_async(all_currencies)
        return api_response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ocurrió un error durante la actualización: {str(e)}")
    
@router.get(
    "/saved-currencies", 
    tags=["Venezuela | Save Data"], 
    summary="Recupera las últimas tasas guardadas en la base de datos con filtros avanzados",
    description="Permite consultar el histórico más reciente de tasas almacenadas. Ofrece filtros por plataforma y opciones para completar datos faltantes en vivo (`fill_missing`), además de forzar el retorno exclusivo del valor del dólar para BCV y Yadio.",
    response_model=BaseResponse[List[CurrencySchema]],
    status_code=status.HTTP_200_OK,
    response_description="Tasas históricas/guardadas recuperadas exitosamente",
    responses={
        200: {"model": BaseResponse[List[CurrencySchema]], "description": "Tasas históricas/guardadas recuperadas exitosamente"},
        408: {"model": ErrorResponse, "description": "Tiempo de espera agotado al recuperar datos de la base de datos"},
        500: {"model": ErrorResponse, "description": "Error al recuperar datos históricos"}
    }
)
async def get_saved_currencies(
    bcv: bool = Query(False, description="Incluir tasas guardadas del BCV."),
    yadio: bool = Query(False, description="Incluir tasas guardadas de Yadio.io."),
    binance: bool = Query(False, description="Incluir tasas guardadas de Binance P2P."),
    fill_missing: bool = Query(False, description="Si es True, completa las plataformas no seleccionadas con datos en vivo."),
    enforce_bcv_dollar: bool = Query(False, description="Si es True, filtra resultados del BCV para mostrar solo el Dólar."),
    enforce_yadio_dollar: bool = Query(False, description="Si es True, filtra resultados de Yadio para mostrar solo el Dólar.")
):
    """
    Retorna las últimas tasas de cambio guardadas en la base de datos.
    Se puede filtrar por una o más fuentes de datos.
    Si no se especifica ninguna fuente y fill_missing es False, se retornarán todas las monedas guardadas.
    Si fill_missing es True, las fuentes en False se obtendrán en vivo.
    """
    try:
        db_platforms = []
        live_tasks = []

        # Lógica para determinar origen de datos por plataforma
        if bcv:
            db_platforms.append(c.BCV_NAME)
        elif fill_missing:
            live_tasks.append(dollar_service.get_raw_bcv_currencies())

        if yadio:
            db_platforms.append(c.YADIO_NAME)
        elif fill_missing:
            live_tasks.append(dollar_service.get_raw_yadio_currencies())

        if binance:
            db_platforms.append(c.BINANCE_NAME)
        elif fill_missing:
            live_tasks.append(dollar_service.get_raw_binance_currencies())

        results = []

        # 1. Obtener datos de BD
        # Si fill_missing es True, solo buscamos en BD si hay plataformas explícitas.
        # Si fill_missing es False, mantenemos el comportamiento original (si no hay flags, trae todo).
        if not fill_missing or db_platforms:
            results.extend(await dollar_service.getSavedCurrencies(platforms=db_platforms))

        # 2. Obtener datos en vivo (si aplica)
        if live_tasks:
            list_of_lists = await asyncio.gather(*live_tasks)
            live_currencies_flat = []
            for sublist in list_of_lists:
                # Manejo especial para BCV que retorna dict {'date':..., 'currencies':...}
                if isinstance(sublist, dict) and "currencies" in sublist:
                    live_currencies_flat.extend(sublist["currencies"])
                elif isinstance(sublist, list):
                    live_currencies_flat.extend(sublist)
            
            # Calculamos el indicador ROC comparando con BD
            if live_currencies_flat:
                processed_live = await dollar_service.calculate_live_changes(live_currencies_flat)
                for currency in processed_live:
                    results.append(dollar_service.serialize_with_image(currency))

        # 3. Filtrado por enforce flags
        final_results = []
        for item in results:
            # Filtro BCV: Si enforce está activo y es BCV, solo pasa si el nombre es "Dolar"
            if enforce_bcv_dollar and item.get('platform') == c.BCV_NAME and item.get('name') != "Dolar":
                continue
            # Filtro Yadio: Si enforce está activo y es Yadio, solo pasa si el nombre es "Dolar"
            if enforce_yadio_dollar and item.get('platform') == c.YADIO_NAME and item.get('name') != "Dolar":
                continue
            final_results.append(item)

        return api_response(final_results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))