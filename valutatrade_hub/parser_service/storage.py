import re
from datetime import UTC, datetime
from math import isfinite

from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.parser_service.config import (
    EXCHANGE_RATES_FILE,
    RATES_FILE,
)

database = DatabaseManager()


def _valid_rate(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Курс должен быть числом.")

    rate = float(value)

    if not isfinite(rate) or rate <= 0:
        raise ValueError("Курс должен быть положительным конечным числом.")

    return rate


def _parse_timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Дата курса должна быть строкой.")

    try:
        timestamp = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except ValueError as error:
        raise ValueError("Некорректная дата курса.") from error

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    else:
        timestamp = timestamp.astimezone(UTC)

    return timestamp

def load_exchange_rates() -> list:
    data = database.read_json(EXCHANGE_RATES_FILE, [])

    if isinstance(data, list):
        return data

    return []


def save_exchange_rates(new_rates: dict) -> None:
    history = load_exchange_rates()
    existing_ids = {item["id"] for item in history if "id" in item}

    for pair, rate_data in new_rates.items():
        parts = pair.split("_", 1)

        if len(parts) != 2:
            raise ValueError(f"Некорректная валютная пара: {pair}")

        from_currency, to_currency = parts

        if not all(re.fullmatch(r"[A-Z]{2,5}", code) for code in parts):
            raise ValueError(f"Некорректный код валюты: {pair}")

        rate = _valid_rate(rate_data["rate"])
        timestamp = rate_data["timestamp"]
        _parse_timestamp(timestamp)

        record_id = f"{from_currency}_{to_currency}_{timestamp}"

        if record_id in existing_ids:
            continue

        history.append(
            {
                "id": record_id,
                "from_currency": from_currency,
                "to_currency": to_currency,
                "rate": rate,
                "timestamp": timestamp,
                "source": rate_data["source"],
                "meta": rate_data.get("meta", {}),
            }
        )
        existing_ids.add(record_id)

    database.write_json(EXCHANGE_RATES_FILE, history)


def _load_cache_pairs(cache):
    if "pairs" in cache and isinstance(cache["pairs"], dict):
        return cache["pairs"]

    pairs = {}

    for pair, value in cache.items():
        if not isinstance(value, dict) or "rate" not in value:
            continue

        pairs[pair] = {
            "rate": value["rate"],
            "updated_at": value.get(
                "updated_at",
                datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            ),
            "source": value.get("source", "legacy-cache"),
        }

    return pairs


def update_rates_cache(new_rates: dict) -> None:
    cache = database.read_json(RATES_FILE, {})

    if not isinstance(cache, dict):
        cache = {}

    pairs = _load_cache_pairs(cache)

    for pair, rate_data in new_rates.items():
        new_timestamp = _parse_timestamp(rate_data["timestamp"])
        current = pairs.get(pair)

        if current:
            current_timestamp = _parse_timestamp(current["updated_at"])

            if new_timestamp <= current_timestamp:
                continue

        pairs[pair] = {
            "rate": _valid_rate(rate_data["rate"]),
            "updated_at": rate_data["timestamp"],
            "source": rate_data["source"],
        }

    database.write_json(
        RATES_FILE,
        {
            "pairs": pairs,
            "last_refresh": datetime.now(UTC).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
        },
    )


def get_latest_rates() -> dict:
    history = load_exchange_rates()
    latest_rates = {}

    for record in history:
        pair = (
            f"{record['from_currency']}_{record['to_currency']}"
        )
        current = latest_rates.get(pair)

        if current is None or _parse_timestamp(
            record["timestamp"]
        ) > _parse_timestamp(current["timestamp"]):
            latest_rates[pair] = record

    return latest_rates


def load_rates_cache() -> dict:
    cache = database.read_json(RATES_FILE, {})

    if not isinstance(cache, dict):
        return {}

    return {
        "pairs": _load_cache_pairs(cache),
        "last_refresh": cache.get("last_refresh"),
    }