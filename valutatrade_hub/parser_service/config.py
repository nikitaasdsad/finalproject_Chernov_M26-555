import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_DIR / "data"


@dataclass(frozen=True)
class ParserConfig:
    exchange_rate_api_key: str = field(
        default_factory=lambda: os.getenv("EXCHANGE_RATE_API_KEY", "")
    )
    coingecko_url: str = "https://api.coingecko.com/api/v3/simple/price"
    exchangerate_api_url: str = "https://v6.exchangerate-api.com/v6"
    base_fiat_currency: str = "USD"
    fiat_currencies: tuple[str, ...] = ("USD", "EUR", "GBP", "RUB")
    crypto_currencies: tuple[str, ...] = ("BTC", "ETH", "SOL")
    crypto_id_map: dict[str, str] = field(
        default_factory=lambda: {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
        }
    )
    rates_file_path: Path = DATA_DIR / "rates.json"
    history_file_path: Path = DATA_DIR / "exchange_rates.json"
    request_timeout: int = 10
    update_interval_seconds: int = 300

CONFIG = ParserConfig()

EXCHANGE_RATE_API_KEY = CONFIG.exchange_rate_api_key
COINGECKO_API_URL = CONFIG.coingecko_url
EXCHANGE_RATE_API_URL = (
    f"{CONFIG.exchangerate_api_url}/"
    f"{EXCHANGE_RATE_API_KEY}/latest/{CONFIG.base_fiat_currency}"
)
BASE_FIAT_CURRENCY = CONFIG.base_fiat_currency
FIAT_CURRENCIES = list(CONFIG.fiat_currencies)
CRYPTO_CURRENCIES = list(CONFIG.crypto_currencies)
CRYPTO_ID_MAP = CONFIG.crypto_id_map
REQUEST_TIMEOUT = CONFIG.request_timeout
UPDATE_INTERVAL_SECONDS = CONFIG.update_interval_seconds
RATES_FILE = CONFIG.rates_file_path
EXCHANGE_RATES_FILE = CONFIG.history_file_path