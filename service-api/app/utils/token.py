from __future__ import annotations

import secrets
import string


_BASE62_ALPHABET = string.digits + string.ascii_lowercase + string.ascii_uppercase


def base62_encode(number: int) -> str:
    if number == 0:
        return _BASE62_ALPHABET[0]

    chars: list[str] = []
    base = len(_BASE62_ALPHABET)

    while number > 0:
        number, remainder = divmod(number, base)
        chars.append(_BASE62_ALPHABET[remainder])

    return "".join(reversed(chars))


def generate_token(num_bytes: int = 32) -> str:
    random_bytes = secrets.token_bytes(num_bytes)
    number = int.from_bytes(random_bytes, byteorder="big", signed=False)
    return base62_encode(number)


__all__ = ["generate_token", "base62_encode"]
