"""Excepciones tipadas para fallos de las fuentes externas de tasas.

Permiten que la capa de servicios propague un error *semántico* (timeout,
fuente caída, respuesta no interpretable) en lugar de devolver una lista vacía.
Así el controlador lo traduce a un código HTTP adecuado (408 / 502) en vez de
responder un 200 con datos vacíos o un 500 confuso.
"""
from contextlib import contextmanager

import httpx

from api.utils.constants.constants import Constants as c


class ExternalSourceError(Exception):
    """Error base al obtener datos de una fuente externa (BCV, Yadio, Binance, Bybit, Airtm, Exchange Monitor).

    Lleva el código HTTP con el que el controlador debe responder
    (``status_code``) y un mensaje legible para el consumidor de la API
    (``message``).
    """

    status_code = c.STATUS_BAD_GATEWAY
    message_template = c.SOURCE_UNAVAILABLE_MSG

    def __init__(self, source: str, detail: str = c.EMPTY_STRING):
        self.source = source
        self.message = self.message_template.format(source=source)
        if detail:
            self.message = f"{self.message} ({detail})"
        super().__init__(self.message)


class SourceTimeoutError(ExternalSourceError):
    """La fuente no respondió dentro del tiempo límite."""

    status_code = c.STATUS_REQUEST_TIMEOUT
    message_template = c.SOURCE_TIMEOUT_MSG


class SourceUnavailableError(ExternalSourceError):
    """La fuente es inaccesible o respondió con un estado HTTP de error."""

    status_code = c.STATUS_BAD_GATEWAY
    message_template = c.SOURCE_UNAVAILABLE_MSG


class SourceParsingError(ExternalSourceError):
    """La respuesta de la fuente no pudo interpretarse (estructura cambiada)."""

    status_code = c.STATUS_BAD_GATEWAY
    message_template = c.SOURCE_PARSING_MSG


class SourceEmptyError(ExternalSourceError):
    """La fuente respondió correctamente pero sin ofertas/datos utilizables.

    Caso típico: Binance P2P devuelve una lista vacía (sin ofertas, rate-limit
    silencioso) y no hay precios que promediar. Se distingue del parsing error
    para no confundir "estructura cambiada" con "no hay datos ahora mismo".
    """

    status_code = c.STATUS_BAD_GATEWAY
    message_template = c.SOURCE_EMPTY_MSG


@contextmanager
def source_guard(source: str):
    """Traduce fallos de red o de parseo en ``ExternalSourceError`` tipados.

    Envuelve un bloque de scraping o de consulta a una API externa: convierte
    los errores de ``httpx`` (timeout, conexión, estado de error) y los fallos
    de interpretación de la respuesta en excepciones de fuente, para que nunca
    se enmascaren como una lista vacía.

    Uso::

        with source_guard(c.BCV_NAME):
            content = await self.client.get_content(...)
            ...  # scraping / parseo
            return {...}
    """
    try:
        yield
    except ExternalSourceError:
        # Ya viene tipada (p. ej. de un guard anidado): se propaga tal cual.
        raise
    except httpx.TimeoutException as e:
        raise SourceTimeoutError(source) from e
    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        raise SourceUnavailableError(source, detail=str(e)) from e
    except (IndexError, AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError) as e:
        raise SourceParsingError(source, detail=str(e)) from e
