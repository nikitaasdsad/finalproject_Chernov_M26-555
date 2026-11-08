from functools import wraps
from inspect import signature

from valutatrade_hub.logging_config import setup_logging

logger = setup_logging()


def log_action(action: str | None = None, verbose: bool = False):
    def decorator(function):
        operation = action or function.__name__.upper()
        function_signature = signature(function)

        @wraps(function)
        def wrapper(*args, **kwargs):
            bound = function_signature.bind_partial(*args, **kwargs)
            values = bound.arguments

            user = function.__globals__.get("current_user")
            username = user.username if user is not None else values.get("username", "anonymous")
            currency = values.get("currency", values.get("currency_code", "-"))
            amount = values.get("amount", "-")
            rate = values.get("rate", "-")
            base = values.get("base", "USD")

            details = (
                f"{operation} user='{username}' currency='{currency}' "
                f"amount={amount} rate={rate} base='{base}'"
            )

            try:
                result = function(*args, **kwargs)
                message = f"{details} result=OK"

                if verbose:
                    message += f" details='{result}'"

                logger.info(message)
                return result

            except Exception as error:
                logger.info(
                    "%s result=ERROR error_type=%s error_message='%s'",
                    details,
                    type(error).__name__,
                    str(error),
                )
                raise

        return wrapper

    return decorator
