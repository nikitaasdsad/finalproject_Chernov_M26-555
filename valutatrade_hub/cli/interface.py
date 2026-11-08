import shlex

from valutatrade_hub.core import usecases


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
                    "exit"
                )
                continue

            result = execute_command(command)

            if result:
                print(result)

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