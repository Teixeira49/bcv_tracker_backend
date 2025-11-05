from bs4 import BeautifulSoup
import requests
import os
import certifi
from datetime import datetime
from typing import List, Optional

from api.models.bcv_currency import BcvCurrency
from api.models.bd_currency import Base, Currency
from api.services.bd_service import save_currencies_to_db, SessionLocal
from api.utils.constants import Constants

class DollarService:
    def getDollarValueByBCV():
        url = requests.get("https://www.bcv.org.ve/", verify=False)
        if url.status_code == 200:
            soup = BeautifulSoup(url.content, "html.parser")
            x=soup.findAll(id="dolar")
            print(str(x[0]))

    async def getCurrenciesByBCV():
        try: 
            print("Fetching currencies from BCV...")
            url = requests.get(Constants.BCV_URL, verify=False)
            elements = []
            if url.status_code == 200:
                soup = BeautifulSoup(url.content, "html.parser")
                date = soup.findAll(class_='date-display-single')
                checkDate = DollarService.validateDate(date[0].attrs.get('content')) if date else False
                currencies = soup.findAll(class_="col-sm-12 col-xs-12")
                for item in currencies: 
                    getImage, getCode, getCurrency, getName  = item.find(class_='icono_bss_blanco1'), item.find('span'), item.find('strong'), item.attrs.get('id')
                    elements.append(
                        DollarService.createBCVCurrency(
                            getCode,
                            getName,
                            getImage,
                            getCurrency,
                            checkDate
                        )
                    )
            save_currencies_to_db(elements)
            return elements
        except Exception as e:
            print(f"An error occurred: {e}")
            return []
        
    async def getSavedCurrencies(today_data: Optional[bool] = None):
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
                    "linkImage": r.linkImage,
                    "exchangeRate": r.exchangeRate,
                    "createDate": r.createDate.isoformat() if r.createDate else None,
                    "updateDate": r.updateDate.isoformat() if r.updateDate else None,
                    "todayData": r.todayData
                })
            return result
        except Exception as e:
            print(f"An error occurred while fetching saved currencies: {e}")
            return []
        finally:
            session.close()
        
    def validateDate(date_str: str) -> bool:
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return date_obj.date() == datetime.utcnow().strftime("%Y-%m-%d")
        except ValueError:
            return False


    def createBCVCurrency(code, name, linkImage, exchangeRate, today) -> Currency:
        return Currency(
            code=str(code.text.strip().replace(' ', '')) if code else '',
            name=str(name.strip()).capitalize() if name else '',
            linkImage=Constants.BCV_URL.replace('ve/', 've') + str(linkImage.attrs.get('src')) if linkImage else '',
            exchangeRate=float(exchangeRate.text.replace(',', '.')) if exchangeRate else 0.0,
            createDate=datetime.utcnow(),
            updateDate=datetime.utcnow(),
            todayData=today
        )
    