from api.core.config.config import Config as c

class DollarEndpoints:

    OFF_MKT = f'{c.OFFICIAL_URL}/'

    PAR_MKT_A = f'{c.PARALLEL_MARKET_A_URL}/bapi/c2c/v2/'

    PAR_MKT_B = f'{c.PARALLEL_MARKET_B_URL}/'

    PAR_MKT_C = f'{c.PARALLEL_MARKET_C_URL}/'

    PAR_MKT_D = f'{c.PARALLEL_MARKET_D_URL}/'

    PAR_MKT_E = f'{c.PARALLEL_MARKET_E_URL}/v3/c2c/'

    # Exchange Monitor renderiza las tasas del lado del cliente: la página HTML
    # solo trae el token CSRF; los valores se piden por separado al endpoint de
    # datos (JSON). Guardamos ambos: la página (para el token + cookie de sesión)
    # y el endpoint de datos de Venezuela.
    EXCHANGE_MONITOR_PAGE = f'{c.PARALLEL_MARKET_D_URL}/dolar-venezuela'

    EXCHANGE_MONITOR_ORIGIN = c.PARALLEL_MARKET_D_URL

    @classmethod
    def getParMktRate(cls, target: str, base: str):
        return cls.PAR_MKT_B + f"rate/{target}/{base}"

    @classmethod
    def getParMktExRate(cls, base: str):
        return cls.PAR_MKT_B + f"exrates/{base}"

    @classmethod
    def getParMktP2P(cls):
        return cls.PAR_MKT_A + "friendly/c2c/adv/search"

    @classmethod
    def getParMktBybitP2P(cls):
        return cls.PAR_MKT_C + "fiat/otc/item/online"

    @classmethod
    def getExchangeMonitorData(cls):
        return cls.PAR_MKT_D + "data/rates/ve"

    @classmethod
    def getOkxP2P(cls):
        return cls.PAR_MKT_E + "tradingOrders/books"