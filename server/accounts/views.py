import pyotp
import segno
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.models import TOTPDevice

PENDING_KEY = "pending_user_id"
NEXT_KEY = "pending_next"
MAX_ATTEMPTS = 5
MAX_PASSWORD_FAILURES = 10
LOCK_SECONDS = 900
BACKEND = "django.contrib.auth.backends.ModelBackend"
WRONG_CODE = "인증 코드가 올바르지 않습니다."
WRONG_LOGIN = "아이디 또는 비밀번호가 올바르지 않습니다."
LOCKED = "잠시 후 다시 시도하세요."


def _otp_key(user) -> str:
    return f"otp-fail:{user.pk}"


def _login_key(username: str) -> str:
    return f"login-fail:{username.lower()}"


def _failures(key: str) -> int:
    return cache.get(key, 0)


def _record_failure(key: str) -> int:
    """LOCK_SECONDS 고정 창 안의 실패 횟수를 올리고 새 값을 돌려준다."""
    cache.add(key, 0, LOCK_SECONDS)
    return cache.incr(key)


def _otp_locked(user) -> bool:
    return _failures(_otp_key(user)) >= MAX_ATTEMPTS


def _safe_next(request: HttpRequest, url: str | None) -> str:
    if url and url_has_allowed_host_and_scheme(
        url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return url
    return "/"


def _clear_pending(request: HttpRequest) -> None:
    for key in (PENDING_KEY, NEXT_KEY):
        request.session.pop(key, None)


def _pending_user(request: HttpRequest):
    user_id = request.session.get(PENDING_KEY)
    if user_id is None:
        return None
    return get_user_model().objects.filter(pk=user_id, is_active=True, is_staff=True).first()


def _finish_login(request: HttpRequest, user) -> HttpResponse:
    next_url = request.session.get(NEXT_KEY, "/")
    cache.delete(_otp_key(user))
    _clear_pending(request)
    login(request, user, backend=BACKEND)
    return redirect(next_url)


def login_view(request: HttpRequest) -> HttpResponse:
    error = ""
    if request.method == "POST":
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        if _failures(_login_key(username)) >= MAX_PASSWORD_FAILURES:
            error = LOCKED
        else:
            user = authenticate(request, username=username, password=password)
            if user is not None and user.is_staff:
                if _otp_locked(user):
                    error = LOCKED
                else:
                    request.session[PENDING_KEY] = user.pk
                    request.session[NEXT_KEY] = _safe_next(request, request.POST.get("next"))
                    if TOTPDevice.objects.filter(user=user, confirmed=True).exists():
                        return redirect("accounts:otp")
                    return redirect("accounts:otp_setup")
            else:
                _record_failure(_login_key(username))
                error = WRONG_LOGIN
    return render(
        request, "accounts/login.html", {"error": error, "next": request.GET.get("next", "")}
    )


def otp_view(request: HttpRequest) -> HttpResponse:
    user = _pending_user(request)
    if user is None:
        return redirect("accounts:login")
    if _otp_locked(user):
        _clear_pending(request)
        return redirect("accounts:login")
    device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
    if device is None:
        return redirect("accounts:otp_setup")
    error = ""
    if request.method == "POST":
        if device.verify(request.POST.get("code", "")):
            return _finish_login(request, user)
        if _record_failure(_otp_key(user)) >= MAX_ATTEMPTS:
            _clear_pending(request)
            return redirect("accounts:login")
        error = WRONG_CODE
    return render(request, "accounts/otp.html", {"error": error})


def otp_setup_view(request: HttpRequest) -> HttpResponse:
    user = _pending_user(request)
    if user is None:
        return redirect("accounts:login")
    if _otp_locked(user):
        _clear_pending(request)
        return redirect("accounts:login")
    if TOTPDevice.objects.filter(user=user, confirmed=True).exists():
        return redirect("accounts:otp")
    device, _ = TOTPDevice.objects.get_or_create(
        user=user, defaults={"secret": pyotp.random_base32()}
    )
    error = ""
    if request.method == "POST":
        if device.verify(request.POST.get("code", "")):
            device.confirmed = True
            device.save(update_fields=["confirmed"])
            return _finish_login(request, user)
        if _record_failure(_otp_key(user)) >= MAX_ATTEMPTS:
            _clear_pending(request)
            return redirect("accounts:login")
        error = WRONG_CODE
    uri = pyotp.TOTP(device.secret).provisioning_uri(name=user.get_username(), issuer_name="WCMS")
    context = {
        "error": error,
        "qr_svg": segno.make(uri, error="m").svg_inline(scale=5),
        "secret": device.secret,
    }
    return render(request, "accounts/otp_setup.html", context)


@require_POST
def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("/")
