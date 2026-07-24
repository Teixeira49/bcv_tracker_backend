"""Body estructurado y máquina de estados por mercado (issue #71).

Reemplaza la maraña de flags booleanos (`bcv, yadio, ...`, `fill_missing`,
`enforce_*`) de `update-currencies` y `saved-currencies` por un **Body** validado
con Pydantic que describe, **por mercado**, su estado (`mode`).

Estados (máquina de estados por mercado):

- ``off``            — no se envía/persiste ni se lee ese mercado.
- ``solo-dolar``     — en vivo, solo el dólar (USD).
- ``todas``          — en vivo, todas sus divisas.
- ``bd-solo-dolar``  — desde BD, solo el dólar.
- ``bd-todas``       — desde BD, todas sus divisas.
- ``average``        — [cripto] en vivo, promedio por activo (buy+sell)/2.
- ``ambas``          — [cripto] en vivo, ambos lados (buy y sell).
- ``own``            — [Exchange Monitor] solo su valor propio ("Exchange Monitor").
- ``own+monitor``    — [Exchange Monitor] valor propio + promedio ("Monitor Dólar").

El comportamiento por defecto de un mercado **no mencionado** en el Body es
``off`` (no se toca). Agregar un mercado nuevo no requiere params nuevos: basta
su entrada en ``MarketName`` y su set de estados permitidos.
"""
from enum import Enum
from typing import Dict

from pydantic import BaseModel, ConfigDict, Field, field_validator

from api.utils.constants.constants import Constants as c


class MarketName(str, Enum):
    """Mercados soportados (clave del Body)."""
    BCV = "bcv"
    YADIO = "yadio"
    BINANCE = "binance"
    BYBIT = "bybit"
    OKX = "okx"
    BITGET = "bitget"
    AIRTM = "airtm"
    DOLARAPI = "dolarapi"
    EXCHANGE_MONITOR = "exchange_monitor"


class MarketMode(str, Enum):
    """Estado (modo) de un mercado dentro del Body."""
    OFF = "off"
    LIVE_DOLLAR = "solo-dolar"
    LIVE_ALL = "todas"
    DB_DOLLAR = "bd-solo-dolar"
    DB_ALL = "bd-todas"
    # Específicos de mercados cripto.
    AVERAGE = "average"
    BOTH = "ambas"
    # Específicos de Exchange Monitor.
    EM_OWN = "own"
    EM_OWN_MONITOR = "own+monitor"


# --- Clasificación de modos (fuente y alcance) ------------------------------
# Modos que leen de la BD.
DB_MODES = frozenset({MarketMode.DB_DOLLAR, MarketMode.DB_ALL})
# Modos que consultan en vivo (fetch a la fuente).
LIVE_MODES = frozenset({
    MarketMode.LIVE_DOLLAR, MarketMode.LIVE_ALL,
    MarketMode.AVERAGE, MarketMode.BOTH,
    MarketMode.EM_OWN, MarketMode.EM_OWN_MONITOR,
})
# Modos que restringen al dólar (USD).
DOLLAR_ONLY_MODES = frozenset({MarketMode.LIVE_DOLLAR, MarketMode.DB_DOLLAR})


# --- Modos permitidos por mercado -------------------------------------------
_GENERIC_FIAT = frozenset({
    MarketMode.OFF, MarketMode.LIVE_DOLLAR, MarketMode.LIVE_ALL,
    MarketMode.DB_DOLLAR, MarketMode.DB_ALL,
})
# Mercados cripto (Binance/Bybit/OKX/Bitget): no tienen "dólar" propio (operan
# USDT/USDC), su vivo se expresa con average|ambas; la BD se lee completa.
_CRYPTO = frozenset({
    MarketMode.OFF, MarketMode.AVERAGE, MarketMode.BOTH, MarketMode.DB_ALL,
})
_EXCHANGE_MONITOR = frozenset({
    MarketMode.OFF, MarketMode.EM_OWN, MarketMode.EM_OWN_MONITOR,
    MarketMode.DB_ALL,
})

ALLOWED_MODES = {
    MarketName.BCV: _GENERIC_FIAT,
    MarketName.YADIO: _GENERIC_FIAT,
    MarketName.AIRTM: _GENERIC_FIAT,
    MarketName.DOLARAPI: _GENERIC_FIAT,
    MarketName.BINANCE: _CRYPTO,
    MarketName.BYBIT: _CRYPTO,
    MarketName.OKX: _CRYPTO,
    MarketName.BITGET: _CRYPTO,
    MarketName.EXCHANGE_MONITOR: _EXCHANGE_MONITOR,
}

# Nombre de plataforma (Constants) por mercado, para mapear a los servicios.
PLATFORM_BY_MARKET = {
    MarketName.BCV: c.BCV_NAME,
    MarketName.YADIO: c.YADIO_NAME,
    MarketName.BINANCE: c.BINANCE_NAME,
    MarketName.BYBIT: c.BYBIT_NAME,
    MarketName.OKX: c.OKX_NAME,
    MarketName.BITGET: c.BITGET_NAME,
    MarketName.AIRTM: c.AIRTM_NAME,
    MarketName.DOLARAPI: c.DOLARAPI_NAME,
    MarketName.EXCHANGE_MONITOR: c.EXCHANGE_MONITOR_NAME,
}


class MarketSelection(BaseModel):
    """Body por mercado. ``markets`` mapea cada mercado a su estado (``mode``).

    Un mercado ausente se trata como ``off`` (default documentado). Se valida que
    cada combinación (mercado, modo) sea admisible según ``ALLOWED_MODES``.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "markets": {
                        "bcv": "bd-solo-dolar",
                        "binance": "average",
                        "exchange_monitor": "own+monitor",
                    }
                }
            ]
        }
    )

    markets: Dict[MarketName, MarketMode] = Field(
        default_factory=dict,
        description="Estado por mercado. Un mercado ausente equivale a 'off'.",
    )

    @field_validator("markets")
    @classmethod
    def _validate_allowed(cls, value):
        for market, mode in value.items():
            allowed = ALLOWED_MODES.get(market, frozenset())
            if mode not in allowed:
                allowed_str = ", ".join(sorted(m.value for m in allowed))
                raise ValueError(
                    f"El modo '{mode.value}' no es válido para el mercado "
                    f"'{market.value}'. Modos permitidos: {allowed_str}."
                )
        return value

    def active(self) -> Dict[MarketName, MarketMode]:
        """Mercados con un modo distinto de ``off`` (los que hacen algo)."""
        return {m: mode for m, mode in self.markets.items() if mode != MarketMode.OFF}
