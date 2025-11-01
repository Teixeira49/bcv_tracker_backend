from bs4 import BeautifulSoup
import requests
import sqlite3
import os
import certifi
from datetime import datetime
from typing import List, Optional

from models.bcv_currency import BcvCurrency
from models.bd_currency import Base, Currency
from services.bd_service import save_currencies_to_db
from utils.constants import Constants

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
        try:
            db_path = Constants.DB_FILE
            if not db_path or not os.path.isfile(db_path):
                # BD no encontrada -> devolver lista vacía o error 404 según prefieras
                return []
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            if today_data is None:
                cur.execute("""
                    SELECT id, code, name, linkImage, exchangeRate, createDate, updateDate, todayData
                    FROM currencies
                    ORDER BY id DESC
                """)
            else:
                # SQLite stores booleans as 0/1
                cur.execute("""
                    SELECT id, code, name, linkImage, exchangeRate, createDate, updateDate, todayData
                    FROM currencies
                    WHERE todayData = ?
                    ORDER BY id DESC
                """, (1 if today_data else 0,))
            rows = cur.fetchall()
            result = []
            for r in rows:
                result.append({
                    "id": r["id"],
                    "code": r["code"],
                    "name": r["name"],
                    "linkImage": r["linkImage"],
                    "exchangeRate": r["exchangeRate"],
                    "createDate": r["createDate"],
                    "updateDate": r["updateDate"],
                    "todayData": bool(r["todayData"])
                })
            conn.close()
            return result
        except Exception as e:
            print(f"An error occurred while fetching saved currencies: {e}")
            return []
        
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
    