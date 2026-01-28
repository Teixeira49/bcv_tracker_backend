from bs4 import BeautifulSoup
import json
import httpx
from datetime import datetime
from typing import Optional

from api.core.client.http_client import HttpClient
from api.models.bd_currency import Currency
from api.services.bd_service import save_currencies_to_db, SessionLocal
from api.utils.constants.constants import Constants as c
from api.utils.constants.scrapping_tags import ScrappingTags as tag
from api.utils.helpers.helper import Helper

from api.services.dollar_endpoints import DollarEndpoints as endpoints

class DollarService:
    def __init__(self):
        self.client = HttpClient()
        self.helper = Helper()

    async def getDollarValueByBCV(self):
        content = await self.client.get_content(endpoints.OFF_MKT, verify=c.VERIFY)
        soup = BeautifulSoup(content, c.F_HTML)
        soup_target=soup.findAll(id=tag.ID_DOLAR)
        item = soup_target[0]
        getCode, getCurrency, getName  = item.find(tag.CLASS_CODE), item.find(tag.CLASS_NAME), item.attrs.get(tag.KEY_NAME)
        currency = self.createCurrency(getCode.text, getName, self.helper.formatCuValue(getCurrency.text))
        return self.serialize_with_image(currency)
    
    async def getCurrenciesByBCV(self):
        try: 
            url = await self.client.get_content(endpoints.OFF_MKT, verify=c.VERIFY)
            elements = []
            soup = BeautifulSoup(url, c.F_HTML)
            date_elements = soup.findAll(class_=tag.CLASS_DATE)
            # Extraemos el string de la fecha de forma segura
            date_str = date_elements[0].attrs.get(tag.KEY_DATE) if date_elements else None
            
            currencies = soup.findAll(class_=tag.CLASS_CURRENCY)
            for item in currencies: 
                getCode, getCurrency, getName = item.find(tag.CLASS_CODE), item.find(tag.CLASS_NAME), item.attrs.get(tag.KEY_NAME)
                elements.append(
                    self.createCurrency(
                        getCode.text,
                        getName,
                        self.helper.formatCuValue(getCurrency.text)
                    )
                )
            
            # Guardamos en base de datos
            #save_currencies_to_db(elements)
            
            # Convertimos los objetos Currency a diccionarios serializables para JSON
            serialized_currencies = [self.serialize_with_image(e) for e in elements]
            
            return {"date": date_str, "currencies": serialized_currencies}
        except Exception as e:
            print(f"An error occurred: {e}")
            return []

    async def getCurrenciesByYadio(self):
        response = await self.client.get(endpoints.getParMktExRate("VES"))
        currencies = [ self.createCurrency(
                "USD",
                "Dolar",
                response["VES"]["VES"] / response["VES"]["USD"],
                c.YADIO_NAME
            ),
            self.createCurrency(
                "EUR",
                "Euro",
                response["VES"]["VES"] / response["VES"]["EUR"],
                c.YADIO_NAME
            ),
            self.createCurrency(
                "BTC",
                "Bitcoin",
                response["BTC"],
                c.YADIO_NAME
            )
        ]
        return [self.serialize_with_image(cur) for cur in currencies]
        
    async def getDollarByYadio(self):
        response = await self.client.get(endpoints.getParMktRate("VES", "USD"))
        currency = self.createCurrency(
                "USD",
                "Dolar",
                response["rate"],
                c.YADIO_NAME
            )
        return self.serialize_with_image(currency)
    
    async def getCurrenciesByBinance(self, client: httpx.AsyncClient, asset: str = "USDT", fiat: str = "VES", tradeType: str = "Buy"):
        dataPayload = {
            "asset": asset,
            "fiat": fiat,
            "page": 1,
            "rows": 10,
            "payTypes": [],
            "tradeType": tradeType,
            "publisherType": None
        } # "merchantCheck": False,
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json"
        }
        response = await self.client.post(endpoints.getParMktP2P(), data=json.dumps(dataPayload), headers=headers)
        advisors = response["data"]
        prices = []
        for advisor in advisors:
            print(advisor)
            prices.append(float(advisor["adv"]["price"]))
        average = sum(prices) / len(prices)

        return self.createCurrency(
            asset,
            "{}-{}".format("Tether" if asset == "USDT" else "USD Coin", tradeType),
            average,
            c.BINANCE_NAME
        )
     
    
    """   
    async def getSavedCurrencies(self, today_data: Optional[bool] = None):
        session = SessionLocal()
        try:
            query = session.query(Currency)

            if today_data is None:
                rows = query.order_by(Currency.id.desc()).all()
            else:
                rows = query.filter(Currency.todayData == today_data).order_by(Currency.id.desc()).all()

            result = []
            for r in rows:
                result.append({
                    "id": r.id,
                    "code": r.code,
                    "name": r.name,
                    "symbolLinkImage": r.symbolLinkImage,
                    "value": r.value,
                    "createDate": r.createDate.isoformat() if r.createDate else None,
                    "updateDate": r.updateDate.isoformat() if r.updateDate else None,
                })
            return result
        except Exception as e:
            print(f"An error occurred while fetching saved currencies: {e}")
            return []
        finally:
            session.close()
        """ 

    def createCurrency(self, code: str = c.EMPTY_STRING, name: str = c.EMPTY_STRING, value:float = 0.0, platform: str = c.BCV_NAME) -> Currency:
        return Currency(
            code=code.strip(),
            name=name.strip().capitalize(),
            platform=platform,
            value=value,
            createDate=Helper().getZoneTime(),
            updateDate=Helper().getZoneTime()
        )

    def serialize_with_image(self, currency: Currency) -> dict:
        """Serializa el objeto Currency y añade el link de la imagen de la plataforma."""
        data = currency.to_dict()
        platform_images = {
            c.BCV_NAME: c.BCV_LOGO_URL,
            c.YADIO_NAME: c.YADIO_LOGO_URL,
            c.BINANCE_NAME: c.BINANCE_LOGO_URL
        }
        data['platform_img'] = platform_images.get(currency.platform, "")
        return data