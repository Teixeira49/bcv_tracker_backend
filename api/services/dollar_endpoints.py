from api.core.config.config import Config as c

class DollarEndpoints:

    OFF_MKT = f'{c.OFFICIAL_URL}/'

    PAR_MKT_A = f'{c.PARALLEL_MARKET_A_URL}/bapi/c2c/v2/'

    PAR_MKT_B = f'{c.PARALLEL_MARKET_B_URL}/'

    PAR_MKT_C = f'{c.PARALLEL_MARKET_C_URL}/'

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