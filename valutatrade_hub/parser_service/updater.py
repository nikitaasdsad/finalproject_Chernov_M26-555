import logging
from datetime import UTC, datetime

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.storage import (
    save_exchange_rates,
    update_rates_cache,
)

logger = logging.getLogger("valutatrade")


class RatesUpdater:
    def __init__(self, clients=None, storage=None):
        self.clients = (
            clients
            if clients is not None
            else [
                ExchangeRateApiClient(),
                CoinGeckoClient(),
            ]
        )
        self.storage = storage

    def run_update(self, source=None) -> dict:
        clients = self.clients

        if source:
            source = source.strip().lower()

            allowed_sources = {
                "coingecko": CoinGeckoClient,
                "exchangerate": ExchangeRateApiClient,
            }

            if source not in allowed_sources:
                raise ValueError(
                    "Источник должен быть coingecko или exchangerate."
                )

            clients = [
                client
                for client in self.clients
                if isinstance(client, allowed_sources[source])
            ]

        logger.info("Начато обновление курсов валют")

        updated_rates = {}
        errors = []

        for client in clients:
            client_name = client.__class__.__name__

            try:
                rates = client.fetch_rates()

                if not isinstance(rates, dict):
                    raise ApiRequestError(
                        f"{client_name} вернул некорректные данные."
                    )

                updated_rates.update(rates)

                logger.info(
                    "%s: получено курсов: %s",
                    client_name,
                    len(rates),
                )

            except ApiRequestError as error:
                message = f"{client_name}: {error}"
                errors.append(message)
                logger.error(message)

            except Exception as error:
                message = f"{client_name}: {error}"
                errors.append(message)
                logger.exception(message)

        if not updated_rates:
            raise ApiRequestError(
                "; ".join(errors) or "Не удалось получить курсы."
            )

        if self.storage is None:
            save_exchange_rates(updated_rates)
            update_rates_cache(updated_rates)
        else:
            self.storage.save_exchange_rates(updated_rates)
            self.storage.update_rates_cache(updated_rates)

        timestamp = datetime.now(UTC).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

        result = {
            "updated_at": timestamp,
            "updated_count": len(updated_rates),
            "errors": errors,
            "rates": updated_rates,
        }

        logger.info(
            "Обновление завершено. Получено курсов: %s",
            len(updated_rates),
        )

        return result


def update_rates(source=None) -> dict:
    return RatesUpdater().run_update(source=source)