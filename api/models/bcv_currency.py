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