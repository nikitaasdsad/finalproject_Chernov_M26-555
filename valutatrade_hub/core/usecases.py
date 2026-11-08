import json
from datetime import datetime, timedelta
from pathlib import Path

from valutatrade_hub.core.models import Portfolio, User, Wallet

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
USERS_FILE = DATA_DIR / "users.json"
PORTFOLIOS_FILE = DATA_DIR / "portfolios.json"
RATES_FILE = DATA_DIR / "rates.json"

DEFAULT_RATES = {
    "EUR_USD": 1.08,
    "GBP_USD": 1.27,
    "RUB_USD": 0.011,
    "BTC_USD": 59337.21,
    "ETH_USD": 3720.0,
    "USD_USD": 1.0,
}

current_user = None


def _load_json(path: Path, default):
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError as error:
        raise ValueError(f"Файл {path.name} содержит некорректный JSON") from error


def _save_json(path: Path, data) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def _load_portfolio(user: User) -> Portfolio:
    portfolio = Portfolio(user)
    portfolios = _load_json(PORTFOLIOS_FILE, [])

    for item in portfolios:
        if item["user_id"] == user.user_id:
            for code, wallet_data in item["wallets"].items():
                portfolio.add_currency(code, wallet_data["balance"])
            break

    return portfolio


def _save_portfolio(portfolio: Portfolio) -> None:
    portfolios = _load_json(PORTFOLIOS_FILE, [])

    portfolio_data = {
        "user_id": portfolio.user_id,
        "wallets": {
            code: {"balance": wallet.balance}
            for code, wallet in portfolio.wallets.items()
        },
    }

    for index, item in enumerate(portfolios):
        if item["user_id"] == portfolio.user_id:
            portfolios[index] = portfolio_data
            break
    else:
        portfolios.append(portfolio_data)

    _save_json(PORTFOLIOS_FILE, portfolios)


def _get_rate_to_usd(currency_code: str) -> float:
    if currency_code == "USD":
        return 1.0

    rates = _load_json(RATES_FILE, {})
    pair = f"{currency_code}_USD"

    if pair in rates:
        return float(rates[pair]["rate"])

    if currency_code in DEFAULT_RATES:
        return DEFAULT_RATES[currency_code]

    raise ValueError(f"Не удалось получить курс для {currency_code}→USD")


def register(username: str, password: str) -> str:
    if not isinstance(username, str) or not username.strip():
        raise ValueError("Имя пользователя не может быть пустым")

    if not isinstance(password, str) or len(password) < 4:
        raise ValueError("Пароль должен быть не короче 4 символов")

    users = _load_json(USERS_FILE, [])
    username = username.strip()

    if any(item["username"].lower() == username.lower() for item in users):
        raise ValueError(f"Имя пользователя '{username}' уже занято")

    user_id = max((item["user_id"] for item in users), default=0) + 1

    user = User(
        user_id,
        username,
        "temporary_hash",
        "temporary_salt",
        datetime.now(),
    )
    user.change_password(password)

    users.append({
        "user_id": user.user_id,
        "username": user.username,
        "hashed_password": user.hashed_password,
        "salt": user.salt,
        "registration_date": user.registration_date.isoformat(),
    })

    _save_json(USERS_FILE, users)

    portfolios = _load_json(PORTFOLIOS_FILE, [])
    portfolios.append({"user_id": user_id, "wallets": {}})
    _save_json(PORTFOLIOS_FILE, portfolios)

    return f"Пользователь '{username}' зарегистрирован (id={user_id}). Войдите: login"


def login(username: str, password: str) -> str:
    global current_user

    users = _load_json(USERS_FILE, [])

    for item in users:
        if item["username"].lower() == username.lower():
            user = User(
                item["user_id"],
                item["username"],
                item["hashed_password"],
                item["salt"],
                datetime.fromisoformat(item["registration_date"]),
            )

            if not user.verify_password(password):
                raise ValueError("Неверный пароль")

            current_user = user
            return f"Вы вошли как '{user.username}'"

    raise ValueError(f"Пользователь '{username}' не найден")


def show_portfolio(base_currency: str = "USD") -> str:
    if current_user is None:
        raise ValueError("Сначала выполните login")

    base = base_currency.strip().upper()

    if not base:
        raise ValueError("Неизвестная базовая валюта")

    portfolio = _load_portfolio(current_user)
    lines = [f"Портфель пользователя '{current_user.username}' (база: {base}):"]

    if not portfolio.wallets:
        return f"{lines[0]}\nПортфель пуст"

    total = 0.0

    for code, wallet in portfolio.wallets.items():
        value = wallet.balance * _get_rate_to_usd(code) / _get_rate_to_usd(base)
        total += value
        lines.append(f"- {code}: {wallet.balance:.4f} → {value:.2f} {base}")

    lines.append(f"ИТОГО: {total:,.2f} {base}")

    return "\n".join(lines)


def buy(currency: str, amount: float) -> str:
    if current_user is None:
        raise ValueError("Сначала выполните login")

    code = currency.strip().upper()

    if not code:
        raise ValueError("Код валюты не может быть пустым")

    Wallet._validate_amount(amount)

    portfolio = _load_portfolio(current_user)

    if code == "USD":
        raise ValueError("Нельзя покупать USD за USD")

    rate = _get_rate_to_usd(code)

    if "USD" not in portfolio.wallets:
        portfolio.add_currency("USD")

    if code not in portfolio.wallets:
        portfolio.add_currency(code)

    wallet_usd = portfolio.get_wallet("USD")
    wallet_target = portfolio.get_wallet(code)

    previous_balance = wallet_target.balance
    cost = amount * rate

    wallet_usd.withdraw(cost)
    wallet_target.deposit(amount)

    _save_portfolio(portfolio)

    return (
        f"Покупка выполнена: {amount:.4f} {code} "
        f"по курсу {rate:.2f} USD/{code}\n"
        f"Изменения в портфеле:\n"
        f"- {code}: было {previous_balance:.4f} → стало "
        f"{wallet_target.balance:.4f}\n"
        f"Оценочная стоимость покупки: {cost:,.2f} USD"
    )


def sell(currency: str, amount: float) -> str:
    if current_user is None:
        raise ValueError("Сначала выполните login")

    code = currency.strip().upper()

    if not code:
        raise ValueError("Код валюты не может быть пустым")

    Wallet._validate_amount(amount)

    portfolio = _load_portfolio(current_user)

    if code not in portfolio.wallets:
        raise ValueError(
            f"У вас нет кошелька '{code}'. "
            "Добавьте валюту: она создаётся автоматически при первой покупке."
        )

    if code == "USD":
        raise ValueError("Продажа USD за USD не поддерживается")

    rate = _get_rate_to_usd(code)
    wallet_target = portfolio.get_wallet(code)

    previous_balance = wallet_target.balance

    if amount > previous_balance:
        raise ValueError(
            f"Недостаточно средств: доступно {previous_balance:.4f} {code}, "
            f"требуется {amount:.4f} {code}"
        )

    wallet_target.withdraw(amount)

    if "USD" not in portfolio.wallets:
        portfolio.add_currency("USD")

    revenue = amount * rate
    portfolio.get_wallet("USD").deposit(revenue)

    _save_portfolio(portfolio)

    return (
        f"Продажа выполнена: {amount:.4f} {code} "
        f"по курсу {rate:.2f} USD/{code}\n"
        f"Изменения в портфеле:\n"
        f"- {code}: было {previous_balance:.4f} → стало "
        f"{wallet_target.balance:.4f}\n"
        f"Оценочная выручка: {revenue:,.2f} USD"
    )


def get_rate(from_currency: str, to_currency: str) -> str:
    source = from_currency.strip().upper()
    target = to_currency.strip().upper()

    if not source or not target:
        raise ValueError("Коды валют не могут быть пустыми")

    rates = _load_json(RATES_FILE, {})
    pair = f"{source}_{target}"
    reverse_pair = f"{target}_{source}"
    now = datetime.now()

    if source == target:
        rate = 1.0
        updated_at = now
    elif pair in rates:
        cached = rates[pair]
        updated_at = datetime.fromisoformat(cached["updated_at"])

        if now - updated_at > timedelta(minutes=5):
            rate = _get_rate_to_usd(source) / _get_rate_to_usd(target)
            updated_at = now
            rates[pair] = {
                "rate": rate,
                "updated_at": updated_at.isoformat(),
            }
            _save_json(RATES_FILE, rates)
        else:
            rate = float(cached["rate"])
    elif reverse_pair in rates:
        cached = rates[reverse_pair]
        reverse_rate = float(cached["rate"])
        rate = 1 / reverse_rate
        updated_at = datetime.fromisoformat(cached["updated_at"])
    else:
        rate = _get_rate_to_usd(source) / _get_rate_to_usd(target)
        updated_at = now
        rates[pair] = {
            "rate": rate,
            "updated_at": updated_at.isoformat(),
        }
        _save_json(RATES_FILE, rates)

    reverse_rate = 1 / rate

    return (
        f"Курс {source}→{target}: {rate:.8f} "
        f"(обновлено: {updated_at.strftime('%Y-%m-%d %H:%M:%S')})\n"
        f"Обратный курс {target}→{source}: {reverse_rate:.8f}"
    )