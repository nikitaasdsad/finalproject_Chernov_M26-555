from abc import ABC, abstractmethod
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from math import isfinite
from time import perf_counter

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import (
    BASE_FIAT_CURRENCY,
    COINGECKO_API_URL,
    CRYPTO_ID_MAP,
    EXCHANGE_RATE_API_KEY,
    EXCHANGE_RATE_API_URL,
    FIAT_CURRENCIES,
    REQUEST_TIMEOUT,
)


def _timestamp(value=None):
    if value is None:
        moment = datetime.now(UTC)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        moment = datetime.fromtimestamp(value, UTC)
    elif isinstance(value, str):
        try:
            moment = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            try:
                moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError as error:
                raise ApiRequestError("Некорректная дата API.") from error

        moment = moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment.astimezone(UTC)
    else:
        raise ApiRequestError("Некорректный тип даты API.")

    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _validate_rate(value, pair):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ApiRequestError(f"Некорректный тип курса {pair}.")

    rate = float(value)

    if not isfinite(rate) or rate <= 0:
        raise ApiRequestError(f"Некорректное значение курса {pair}.")

    return rate
def _check_response(response, provider):
    status = response.status_code

    if status == 401:
        raise ApiRequestError(
            f"{provider}: неверный API-ключ или отсутствует авторизация."
        )

    if status == 403:
        raise ApiRequestError(
            f"{provider}: доступ к API запрещён."
        )

    if status == 429:
        raise ApiRequestError(
            f"{provider}: превышен лимит запросов. Попробуйте позже."
        )

    if status >= 500:
        raise ApiRequestError(
            f"{provider}: сервер временно недоступен (HTTP {status})."
        )

    if status >= 400:
        raise ApiRequestError(
            f"{provider}: ошибка HTTP {status}."
        )

class BaseApiClient(ABC):
    @abstractmethod
    def fetch_rates(self) -> dict:
        pass


class CoinGeckoClient(BaseApiClient):
    def fetch_rates(self) -> dict:
        parameters = {
            "ids": ",".join(CRYPTO_ID_MAP.values()),
            "vs_currencies": "usd",
            "include_last_updated_at": "true",
        }

        started = perf_counter()

        try:
            response = requests.get(
                COINGECKO_API_URL,
                params=parameters,
                timeout=REQUEST_TIMEOUT,
            )
            _check_response(response, "CoinGecko")
            data = response.json()
        except requests.exceptions.Timeout as error:
            raise ApiRequestError(
                "CoinGecko: превышено время ожидания ответа."
            ) from error
        except requests.exceptions.RequestException as error:
            raise ApiRequestError(
                "CoinGecko: не удалось выполнить запрос."
            ) from error
        except ValueError as error:
            raise ApiRequestError(
                "CoinGecko вернул некорректный JSON."
            ) from error


        if not isinstance(data, dict):
            raise ApiRequestError("CoinGecko вернул некорректные данные.")

        request_ms = round((perf_counter() - started) * 1000)
        result = {}

        for code, coin_id in CRYPTO_ID_MAP.items():
            coin_data = data.get(coin_id)

            if not isinstance(coin_data, dict) or "usd" not in coin_data:
                continue

            pair = f"{code}_USD"
            rate = _validate_rate(coin_data["usd"], pair)
            timestamp = _timestamp(coin_data.get("last_updated_at"))

            result[pair] = {
                "rate": rate,
                "timestamp": timestamp,
                "source": "CoinGecko",
                "meta": {
                    "raw_id": coin_id,
                    "request_ms": request_ms,
                    "status_code": response.status_code,
                    "etag": response.headers.get("ETag"),
                },
            }

        if not result:
            raise ApiRequestError("CoinGecko не вернул курсы.")

        return result


class ExchangeRateApiClient(BaseApiClient):
    def fetch_rates(self) -> dict:
        if not EXCHANGE_RATE_API_KEY:
            raise ApiRequestError(
                "Не задан EXCHANGE_RATE_API_KEY в переменных окружения."
            )

        started = perf_counter()

        try:
            response = requests.get(
                EXCHANGE_RATE_API_URL,
                timeout=REQUEST_TIMEOUT,
            )
            _check_response(response, "ExchangeRate-API")
            data = response.json()
        except requests.exceptions.Timeout as error:
            raise ApiRequestError(
                "ExchangeRate-API: превышено время ожидания ответа."
            ) from error
        except requests.exceptions.RequestException as error:
            raise ApiRequestError(
                "ExchangeRate-API: не удалось выполнить запрос."
            ) from error
        except ValueError as error:
            raise ApiRequestError(
                "ExchangeRate-API вернул некорректный JSON."
            ) from error


        if not isinstance(data, dict):
            raise ApiRequestError(
                "ExchangeRate-API вернул некорректные данные."
            )

        if data.get("result") != "success":
            reason = data.get("error-type", "неизвестная ошибка")
            raise ApiRequestError(f"ExchangeRate-API: {reason}")

        rates = data.get("conversion_rates", data.get("rates"))

        if not isinstance(rates, dict):
            raise ApiRequestError(
                "ExchangeRate-API не вернул список курсов."
            )

        request_ms = round((perf_counter() - started) * 1000)
        timestamp = _timestamp(data.get("time_last_update_utc"))
        result = {}

        for currency in FIAT_CURRENCIES:
            if currency == BASE_FIAT_CURRENCY:
                result[f"{currency}_USD"] = {
                    "rate": 1.0,
                    "timestamp": timestamp,
                    "source": "ExchangeRate-API",
                    "meta": {
                        "raw_id": currency,
                        "request_ms": request_ms,
                        "status_code": response.status_code,
                        "etag": response.headers.get("ETag"),
                    },
                }
                continue

            api_rate = rates.get(currency)

            if api_rate is None:
                continue

            api_rate = _validate_rate(
                api_rate,
                f"{BASE_FIAT_CURRENCY}_{currency}",
            )

            pair = f"{currency}_{BASE_FIAT_CURRENCY}"

            result[pair] = {
                "rate": _validate_rate(1 / api_rate, pair),
                "timestamp": timestamp,
                "source": "ExchangeRate-API",
                "meta": {
                    "raw_id": currency,
                    "request_ms": request_ms,
                    "status_code": response.status_code,
                    "etag": response.headers.get("ETag"),
                },
            }

        if not result:
            raise ApiRequestError(
                "ExchangeRate-API не вернул курсы фиатных валют."
            )

        return result