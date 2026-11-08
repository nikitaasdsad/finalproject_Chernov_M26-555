import shlex

from prettytable import PrettyTable

from valutatrade_hub.core import usecases
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.parser_service.config import CRYPTO_CURRENCIES
from valutatrade_hub.parser_service.scheduler import run_scheduler
from valutatrade_hub.parser_service.storage import load_rates_cache
from valutatrade_hub.parser_service.updater import RatesUpdater


def parse_arguments(arguments: list[str]) -> dict[str, str]:
    result = {}
    index = 0

    while index < len(arguments):
        key = arguments[index]

        if not key.startswith("--"):
            raise ValueError(f"Неизвестный аргумент: {key}")

        if index + 1 >= len(arguments):
            raise ValueError(f"Не указано значение для {key}")

        result[key[2:]] = arguments[index + 1]
        index += 2

    return result


def show_rates(currency=None, top=None, base="USD"):
    cache = load_rates_cache()
    pairs = cache.get("pairs", {})
    last_refresh = cache.get("last_refresh")

    if not pairs:
        return (
            "Локальный кеш курсов пуст. "
            "Выполните 'update-rates', чтобы загрузить данные."
        )

    currency = currency.upper() if currency else None
    base = base.upper()

    base_rate = 1.0

    if base != "USD":
        base_data = pairs.get(f"{base}_USD")

        if not base_data:
            return f"Базовая валюта '{base}' не найдена в кеше."

        base_rate = float(base_data["rate"])

    result = []

    for pair, data in pairs.items():
        from_currency, to_currency = pair.split("_", 1)

        if to_currency != "USD":
            continue

        if currency and from_currency != currency:
            continue

        rate = float(data["rate"]) / base_rate

        result.append(
            {
                "pair": f"{from_currency}_{base}",
                "rate": rate,
                "updated_at": data["updated_at"],
                "crypto": from_currency in CRYPTO_CURRENCIES,
            }
        )

    if currency and not result:
        return f"Курс для '{currency}' не найден в кеше."

    if top is not None:
        if top <= 0:
            return "Количество курсов должно быть положительным."

        result = [item for item in result if item["crypto"]]
        result.sort(key=lambda item: item["rate"], reverse=True)
        result = result[:top]
    else:
        result.sort(key=lambda item: item["pair"])

    if not result:
        return "Курсы по заданным условиям не найдены."

    table = PrettyTable()
    table.field_names = ["Валютная пара", "Курс", "Обновлено"]

    for item in result:
        table.add_row(
            [
                item["pair"],
                f"{item['rate']:.8f}",
                item["updated_at"],
            ]
        )

    return (
        f"Курсы из кеша (последнее обновление: {last_refresh}):\n"
        f"{table}"
    )


def execute_command(command: str) -> str:
    parts = shlex.split(command)

    if not parts:
        return ""

    action = parts[0]
    arguments = parse_arguments(parts[1:])

    if action == "register":
        return usecases.register(
            arguments["username"],
            arguments["password"],
        )

    if action == "login":
        return usecases.login(
            arguments["username"],
            arguments["password"],
        )

    if action == "show-portfolio":
        return usecases.show_portfolio(
            arguments.get("base", "USD"),
        )

    if action == "buy":
        return usecases.buy(
            arguments["currency"],
            float(arguments["amount"]),
        )

    if action == "sell":
        return usecases.sell(
            arguments["currency"],
            float(arguments["amount"]),
        )

    if action == "get-rate":
        return usecases.get_rate(
            arguments["from"],
            arguments["to"],
        )

    if action == "update-rates":
        source = arguments.get("source")
        updater = RatesUpdater()
        result = updater.run_update(source=source)

        message = (
            f"Обновление завершено. Обновлено курсов: "
            f"{result['updated_count']}. "
            f"Время: {result['updated_at']}"
        )

        if result["errors"]:
            message += "\nПредупреждения: " + "; ".join(result["errors"])

        return message

    if action == "show-rates":
        currency = arguments.get("currency")
        top = arguments.get("top")
        base = arguments.get("base", "USD")

        if top is not None:
            top = int(top)

        return show_rates(
            currency=currency,
            top=top,
            base=base,
        )

    if action == "scheduler":
        run_scheduler()
        return ""

    if action in {"exit", "quit"}:
        raise SystemExit

    raise ValueError(f"Неизвестная команда: {action}")


def main() -> None:
    print("ValutaTrade Hub")
    print("Введите help для списка команд или exit для выхода")

    while True:
        try:
            command = input("> ").strip()

            if command == "help":
                print(
                    "register --username NAME --password PASS\n"
                    "login --username NAME --password PASS\n"
                    "show-portfolio --base USD\n"
                    "buy --currency BTC --amount 0.05\n"
                    "sell --currency BTC --amount 0.01\n"
                    "get-rate --from EUR --to USD\n"
                    "update-rates\n"
                    "update-rates --source coingecko\n"
                    "update-rates --source exchangerate\n"
                    "show-rates --currency BTC --base USD\n"
                    "show-rates --top 2 --base EUR\n"
                    "scheduler\n"
                    "exit"
                )
                continue

            result = execute_command(command)

            if result:
                print(result)

        except InsufficientFundsError as error:
            print(error)

        except CurrencyNotFoundError as error:
            print(error)
            print(
                "Поддерживаемые валюты: USD, EUR, GBP, RUB, BTC, ETH, SOL"
            )

        except ApiRequestError as error:
            print(error)
            print("Попробуйте повторить запрос позже.")

        except (ValueError, KeyError, TypeError) as error:
            print(f"Ошибка: {error}")

        except (EOFError, KeyboardInterrupt):
            print("\nДо свидания!")
            break

        except SystemExit:
            print("До свидания!")
            break


if __name__ == "__main__":
    main()