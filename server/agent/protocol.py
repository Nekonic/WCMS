import math

PROTO_VERSION = 1
CLOSE_HELLO_REQUIRED = 4400
CLOSE_UNSUPPORTED_PROTO = 4406
CLOSE_SUPERSEDED = 4409
CLOSE_REVOKED = 4410
STATUS_MIN_INTERVAL = 5.0

NUMBER_LIMITS = {
    "cpu": 100,
    "mem_used": 2**53,
    "mem_total": 2**53,
    "disk_used": 2**53,
    "disk_total": 2**53,
}
SESSIONS = ("active", "locked", "none")


def bearer_token(scope: dict) -> str | None:
    for name, value in scope.get("headers", []):
        if name == b"authorization":
            text = value.decode("latin-1")
            if text.startswith("Bearer "):
                return text[len("Bearer "):].strip() or None
    return None


def _number(value, maximum: float) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and 0 <= value <= maximum
        and math.isfinite(value)
    )


def _text(value, limit: int) -> str | None:
    return value[:limit] if isinstance(value, str) else None


def clean_status(message: dict) -> dict:
    status: dict = {key: message[key] for key, limit in NUMBER_LIMITS.items() if _number(message.get(key), limit)}
    user = _text(message.get("user"), 64)
    if user is not None:
        status["user"] = user
    session = message.get("session")
    status["session"] = session if session in SESSIONS else "none"
    foreground = message.get("foreground")
    if isinstance(foreground, dict):
        process = _text(foreground.get("process"), 128)
        title = _text(foreground.get("title"), 256)
        if process is not None or title is not None:
            status["foreground"] = {"process": process or "", "title": title or ""}
    return status
