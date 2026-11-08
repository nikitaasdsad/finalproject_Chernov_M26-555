from abc import ABC, abstractmethod
from math import isfinite


class Currency(ABC):
    def __init__(self, name: str, code: str):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Название валюты не может быть пустым")

        if not isinstance(code, str):
            raise ValueError("Код валюты должен быть строкой")

        code = code.upper()

        if not 2 <= len(code) <= 5 or not code.isalpha():
            raise ValueError("Код валюты должен содержать от 2 до 5 букв")

        self.name = name.strip()
        self.code = code

    @abstractmethod
    def get_display_info(self) -> str:
        pass


class FiatCurrency(Currency):
    def __init__(self, name: str, code: str, issuing_country: str):
        super().__init__(name, code)

        if not isinstance(issuing_country, str) or not issuing_country.strip():
            raise ValueError("Страна или зона эмиссии не может быть пустой")

        self.issuing_country = issuing_country.strip()

    def get_display_info(self) -> str:
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):
    def __init__(
        self,
        name: str,
        code: str,
        algorithm: str,
        market_cap: float,
    ):
        super().__init__(name, code)

        if not isinstance(algorithm, str) or not algorithm.strip():
            raise ValueError("Алгоритм не может быть пустым")

        if isinstance(market_cap, bool) or not isinstance(market_cap, (int, float)):
            raise ValueError("Капитализация должна быть числом")

        if not isfinite(market_cap) or market_cap < 0:
            raise ValueError("Капитализация должна быть конечным неотрицательным числом")

        self.algorithm = algorithm.strip()
        self.market_cap = float(market_cap)

    def get_display_info(self) -> str:
        return (
            f"[CRYPTO] {self.code} — {self.name} "
            f"(Algo: {self.algorithm}, MCAP: {self.market_cap:.2e})"
        )


_CURRENCIES: dict[str, Currency] = {
    "USD": FiatCurrency("US Dollar", "USD", "United States"),
    "EUR": FiatCurrency("Euro", "EUR", "Eurozone"),
    "GBP": FiatCurrency("British Pound", "GBP", "United Kingdom"),
    "RUB": FiatCurrency("Russian Ruble", "RUB", "Russia"),
    "BTC": CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12),
    "ETH": CryptoCurrency("Ethereum", "ETH", "Ethash", 4.45e11),
" SOL": CryptoCurrency(
    name="Solana",
    code="SOL",
    algorithm="Proof of History",
    market_cap=0,
),
}


def get_currency(code: str) -> Currency:
    if not isinstance(code, str):
        raise ValueError("Код валюты должен быть строкой")

    normalized_code = code.strip().upper()

    try:
        return _CURRENCIES[normalized_code]
    except KeyError:
        from valutatrade_hub.core.exceptions import CurrencyNotFoundError

        raise CurrencyNotFoundError(normalized_code) from None
