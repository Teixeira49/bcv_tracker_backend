from bs4 import BeautifulSoup
import requests

class Constants:
    BCV_URL = "https://www.bcv.org.ve/"
    EMPTY_STRING = ""
    EMPTY_SPACE = " "

class BcvCurrency():
    def __init__(self, code: str, name: str, symbol: str, exchange_rate: float):
        self.code = code
        self.name = name
        self.symbol = symbol
        self.exchange_rate = exchange_rate

    def to_string(self) -> str:
        return f"{self.name} ({self.code}): {self.symbol} at rate {self.exchange_rate}"

    def convert_to_usd(self, amount: float) -> float:
        """Convert the given amount to USD using the exchange rate."""
        return amount / self.exchange_rate

    def convert_from_usd(self, amount: float) -> float:
        """Convert the given amount from USD to this currency using the exchange rate."""
        return amount * self.exchange_rate

    def __repr__(self):
        return f"<BcvCurrency(code={self.code}, name={self.name}, symbol={self.symbol}, exchange_rate={self.exchange_rate})>"

def getDollarValueByBCV():
    url = requests.get("https://www.bcv.org.ve/", verify=False)
    if url.status_code == 200:
        soup = BeautifulSoup(url.content, "html.parser")
        x=soup.findAll(id="dolar")
        print(str(x[0]))

def getCurrenciesByBCV():
    try: 
        url = requests.get(Constants.BCV_URL, verify=False)
        elements = []
        if url.status_code == 200:
            soup = BeautifulSoup(url.content, "html.parser")
            x=soup.findAll(class_="col-sm-12 col-xs-12")
            for item in x: 
                getImage, getCode, getCurrency, getName  = item.find(class_='icono_bss_blanco1'), item.find('span'), item.find('strong'), item.attrs.get('id')
                elements.append(
                    BcvCurrency(
                        code=str(getCode.text.strip().replace(' ', '')) if getCode else '',
                        name=str(getName.strip()).capitalize() if getName else '',
                        symbol=Constants.BCV_URL.replace('ve/', 've') + getImage.attrs.get('src') if getImage else '',
                        exchange_rate=float(getCurrency.text.replace(',', '.')) if getCurrency else 0.0
                    )
                )
        return elements
    except Exception as e:
        print(f"An error occurred: {e}")
        return []


getCurrenciesByBCV()