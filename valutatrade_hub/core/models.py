import hashlib
import hmac
import math
import secrets
from datetime import datetime
from typing import ClassVar


class User:
    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime,
    ) -> None:
        if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("ID пользователя должен быть положительным числом")

        if not isinstance(hashed_password, str) or not hashed_password:
            raise ValueError("Хеш пароля не может быть пустым")

        if not isinstance(salt, str) or not salt:
            raise ValueError("Соль не может быть пустой")

        if not isinstance(registration_date, datetime):
            raise TypeError("Некорректная дата регистрации")

        self._user_id = user_id
        self.username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Имя пользователя не может быть пустым")

        self._username = value.strip()

    @property
    def hashed_password(self) -> str:
        return self._hashed_password

    @property
    def salt(self) -> str:
        return self._salt

    @property
    def registration_date(self) -> datetime:
        return self._registration_date

    def change_password(self, new_password: str) -> None:
        if not isinstance(new_password, str):
            raise TypeError("Пароль должен быть строкой")

        if len(new_password) < 4:
            raise ValueError("Пароль должен содержать минимум 4 символа")

        self._salt = secrets.token_hex(16)

        self._hashed_password = hashlib.sha256(
            (new_password + self._salt).encode("utf-8")
        ).hexdigest()

    def verify_password(self, password: str) -> bool:
        if not isinstance(password, str):
            return False

        hashed = hashlib.sha256((password + self._salt).encode("utf-8")).hexdigest()

        return hmac.compare_digest(hashed, self._hashed_password)

    def get_user_info(self) -> dict:
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }


class Wallet:
    def __init__(self, currency_code: str, balance: float = 0.0) -> None:
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise ValueError("Код валюты не может быть пустым")

        self.currency_code = currency_code.strip().upper()
        self.balance = balance

    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("Баланс должен быть числом")

        if not math.isfinite(value):
            raise ValueError("Баланс должен быть конечным числом")

        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")

        self._balance = float(value)

    @staticmethod
    def _validate_amount(amount: float) -> None:
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise TypeError("Сумма должна быть числом")

        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("Сумма должна быть положительной")

    def deposit(self, amount: float) -> None:
        self._validate_amount(amount)
        self.balance += amount

    def withdraw(self, amount: float) -> None:
        self._validate_amount(amount)

        if amount > self.balance:
            raise ValueError("Недостаточно средств")

        self.balance -= amount

    def get_balance_info(self) -> dict:
        return {
            "currency_code": self.currency_code,
            "balance": self.balance,
        }


class Portfolio:
    exchange_rates: ClassVar[dict[str, float]] = {
        "USD": 1.0,
        "EUR": 1.08,
        "GBP": 1.27,
        "RUB": 0.011,
    }

    def __init__(self, user: User) -> None:
        if not isinstance(user, User):
            raise TypeError("Необходимо передать объект User")

        self._user = user
        self._user_id = user.user_id
        self._wallets: dict[str, Wallet] = {}

    @property
    def user(self) -> User:
        return self._user

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def wallets(self) -> dict[str, Wallet]:
        return self._wallets.copy()

    def add_currency(self, currency_code: str, balance: float = 0.0) -> Wallet:
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise ValueError("Код валюты не может быть пустым")

        code = currency_code.strip().upper()

        if code in self._wallets:
            raise ValueError(f"Кошелёк {code} уже существует")

        wallet = Wallet(code, balance)
        self._wallets[code] = wallet
        return wallet

    def get_wallet(self, currency_code: str) -> Wallet:
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise ValueError("Код валюты не может быть пустым")

        code = currency_code.strip().upper()

        if code not in self._wallets:
            raise ValueError(f"Кошелёк {code} не найден")

        return self._wallets[code]

    def get_total_value(self, base_currency: str = "USD") -> float:
        if not isinstance(base_currency, str):
            raise TypeError("Код валюты должен быть строкой")

        base = base_currency.strip().upper()

        if base not in self.exchange_rates:
            raise ValueError(f"Неизвестная валюта: {base}")

        total_usd = 0.0

        for code, wallet in self._wallets.items():
            if code not in self.exchange_rates:
                raise ValueError(f"Неизвестная валюта: {code}")

            total_usd += wallet.balance * self.exchange_rates[code]

        return total_usd / self.exchange_rates[base]

    def buy_currency(self, currency_code: str, amount: float) -> None:
        code = currency_code.strip().upper()

        if code == "USD":
            raise ValueError("Нельзя покупать USD за USD")

        if code not in self.exchange_rates:
            raise ValueError(f"Неизвестная валюта: {code}")

        Wallet._validate_amount(amount)

        wallet_usd = self.get_wallet("USD")
        wallet_target = self.get_wallet(code)

        cost = amount * self.exchange_rates[code]

        wallet_usd.withdraw(cost)
        wallet_target.deposit(amount)

    def sell_currency(self, currency_code: str, amount: float) -> None:
        code = currency_code.strip().upper()

        if code == "USD":
            raise ValueError("Нельзя продавать USD за USD")

        if code not in self.exchange_rates:
            raise ValueError(f"Неизвестная валюта: {code}")

        Wallet._validate_amount(amount)

        wallet_target = self.get_wallet(code)
        wallet_usd = self.get_wallet("USD")

        wallet_target.withdraw(amount)
        wallet_usd.deposit(amount * self.exchange_rates[code])
