import hmac
import time

import pyotp
from django.conf import settings
from django.db import models

STEP_SECONDS = 30


class TOTPDevice(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="totp"
    )
    secret = models.CharField(max_length=64)
    confirmed = models.BooleanField(default=False)
    last_used_step = models.BigIntegerField(default=0)

    def verify(self, code: str) -> bool:
        code = code.replace(" ", "").strip()
        if not code.isdigit():
            return False
        totp = pyotp.TOTP(self.secret)
        current = int(time.time() // STEP_SECONDS)
        for step in (current - 1, current, current + 1):
            if step <= self.last_used_step:
                continue
            if hmac.compare_digest(totp.at(step * STEP_SECONDS), code):
                self.last_used_step = step
                self.save(update_fields=["last_used_step"])
                return True
        return False
