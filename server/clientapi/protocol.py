NUMBER_FIELDS = ("cpu", "mem_used", "mem_total", "disk_used", "disk_total")
SESSIONS = ("active", "locked", "none")


def pc_group(pc_id: int) -> str:
    return f"pc-{pc_id}"


def bearer_token(scope: dict) -> str | None:
    for name, value in scope.get("headers", []):
        if name == b"authorization":
            text = value.decode("latin-1")
            if text.startswith("Bearer "):
                return text[len("Bearer "):].strip() or None
    return None


def clean_status(message: dict) -> dict:
    status: dict = {}
    for key in NUMBER_FIELDS:
        value = message.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0:
            status[key] = value
    user = message.get("user")
    if isinstance(user, str):
        status["user"] = user[:64]
    session = message.get("session")
    status["session"] = session if session in SESSIONS else "none"
    foreground = message.get("foreground")
    if isinstance(foreground, dict):
        status["foreground"] = {
            "process": str(foreground.get("process", ""))[:128],
            "title": str(foreground.get("title", ""))[:256],
        }
    return status
