from __future__ import annotations

import re


_PASSWORD_DIGIT = re.compile(r".*[0-9].*")
_PASSWORD_LOWER = re.compile(r".*[a-z].*")
_PASSWORD_UPPER = re.compile(r".*[A-Z].*")


def is_password_valid(password: str | None) -> bool:
    if password is None:
        return False

    if len(password) < 8:
        return False

    if not _PASSWORD_DIGIT.match(password):
        return False

    if not _PASSWORD_LOWER.match(password):
        return False

    if not _PASSWORD_UPPER.match(password):
        return False

    return True


__all__ = ["is_password_valid"]
