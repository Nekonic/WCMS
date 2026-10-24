import json

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from labs.models import PC, RegistrationPin

MAX_PIN_FAILURES = 10
PIN_LOCK_SECONDS = 600
MAX_SPECS_BYTES = 16384


def client_ip(request: HttpRequest) -> str:
    header = settings.WCMS_CLIENT_IP_HEADER
    if header and request.META.get(header):
        return request.META[header].split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _error(error: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"error": error}, status=status)


@csrf_exempt
@require_POST
def register(request: HttpRequest) -> JsonResponse:
    fail_key = f"register-fail:{client_ip(request)}"
    if cache.get(fail_key, 0) >= MAX_PIN_FAILURES:
        return _error("too_many_attempts", 429)

    try:
        data = json.loads(request.body)
    except ValueError:
        return _error("bad_json")
    if not isinstance(data, dict):
        return _error("bad_json")

    pin = data.get("pin")
    hostname = data.get("hostname")
    machine_guid = data.get("machine_guid")
    specs = data.get("specs", {})
    version = data.get("version", "")
    if not all(isinstance(v, str) for v in (pin, hostname, machine_guid, version)):
        return _error("bad_fields")
    if not isinstance(specs, dict):
        return _error("bad_fields")
    if not (0 < len(hostname) <= 64 and 0 < len(machine_guid) <= 64 and len(version) <= 20):
        return _error("bad_fields")
    if len(json.dumps(specs)) > MAX_SPECS_BYTES:
        return _error("specs_too_large")

    if not RegistrationPin.consume(pin):
        cache.set(fail_key, cache.get(fail_key, 0) + 1, PIN_LOCK_SECONDS)
        return _error("invalid_pin", 403)

    pc, token = PC.register(
        hostname=hostname, machine_guid=machine_guid, specs=specs, version=version
    )
    return JsonResponse({"pc_id": pc.id, "token": token}, status=201)
