import hmac
import time

import pyotp

STEP_SECONDS = 30


def matching_step(secret: str, code: str) -> int | None:
    """코드가 맞는 30초 구간 번호를 돌려준다. 앞뒤 한 구간까지 허용한다."""
    code = code.replace(" ", "").strip()
    if not (len(code) == 6 and code.isascii() and code.isdigit()):
        return None
    totp = pyotp.TOTP(secret)
    current = int(time.time() // STEP_SECONDS)
    for step in (current - 1, current, current + 1):
        if hmac.compare_digest(totp.at(step * STEP_SECONDS), code):
            return step
    return None
