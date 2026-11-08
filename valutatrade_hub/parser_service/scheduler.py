import logging
import time

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import UPDATE_INTERVAL_SECONDS
from valutatrade_hub.parser_service.updater import update_rates

logger = logging.getLogger("valutatrade")


def run_scheduler() -> None:
    print(
        f"Планировщик запущен. Интервал обновления: "
        f"{UPDATE_INTERVAL_SECONDS} секунд."
    )

    while True:
        try:
            result = update_rates()
            print(
                f"Обновлено курсов: {result['updated_count']}. "
                f"Время: {result['updated_at']}"
            )

            for error in result["errors"]:
                print(f"Предупреждение: {error}")

        except ApiRequestError as error:
            logger.error("Ошибка планировщика: %s", error)
            print(f"Ошибка обновления курсов: {error}")

        except Exception:
            logger.exception("Непредвиденная ошибка планировщика")
            print("Произошла непредвиденная ошибка. Подробности в журнале.")

        print("Следующее обновление через 5 минут.")

        try:
            time.sleep(UPDATE_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            print("\nПланировщик остановлен.")
            break