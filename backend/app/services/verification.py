"""In-memory verification code store with expiration."""
import random
import string
import time
from typing import Optional


# {email: (code, expire_timestamp)}
_store: dict[str, tuple[str, float]] = {}
_CODE_TTL = 600  # 10 minutes


def generate_code(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


def save_code(email: str) -> str:
    code = generate_code()
    _store[email] = (code, time.time() + _CODE_TTL)
    return code


def verify_code(email: str, code: str) -> bool:
    entry = _store.get(email)
    if not entry:
        return False
    saved_code, expire_at = entry
    if time.time() > expire_at:
        _store.pop(email, None)
        return False
    if saved_code != code:
        return False
    _store.pop(email, None)
    return True


def get_code(email: str) -> Optional[str]:
    """Return code if still valid (for dev/debug use)."""
    entry = _store.get(email)
    if not entry:
        return None
    code, expire_at = entry
    if time.time() > expire_at:
        _store.pop(email, None)
        return None
    return code
