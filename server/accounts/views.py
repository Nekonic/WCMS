import pyotp
import segno
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.models import TOTPDevice

PENDING_KEY = "pending_user_id"
NEXT_KEY = "pending_next"
ATTEMPTS_KEY = "otp_attempts"
MAX_ATTEMPTS = 5
BACKEND = "django.contrib.auth.backends.ModelBackend"
WRONG_CODE = "인증 코드가 올바르지 않습니다."


def _safe_next(request: HttpRequest, url: str | None) -> str:
    if url and url_has_allowed_host_and_scheme(
        url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return url
    return "/"


def _clear_pending(request: HttpRequest) -> None:
    for key in (PENDING_KEY, NEXT_KEY, ATTEMPTS_KEY):
        request.session.pop(key, None)


def _pending_user(request: HttpRequest):
    user_id = request.session.get(PENDING_KEY)
    if user_id is None:
        return None
    return get_user_model().objects.filter(pk=user_id, is_active=True, is_staff=True).first()


def _finish_login(request: HttpRequest, user) -> HttpResponse:
    next_url = request.session.get(NEXT_KEY, "/")
    _clear_pending(request)
    login(request, user, backend=BACKEND)
    return redirect(next_url)


def _count_failure(request: HttpRequest) -> bool:
    """실패 횟수를 올리고, 한도에 닿으면 대기 중인 로그인을 버린다."""
    request.session[ATTEMPTS_KEY] = request.session.get(ATTEMPTS_KEY, 0) + 1
    if request.session[ATTEMPTS_KEY] >= MAX_ATTEMPTS:
        _clear_pending(request)
        return True
    return False


def login_view(request: HttpRequest) -> HttpResponse:
    error = ""
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username", ""),
            password=request.POST.get("password", ""),
        )
        if user is not None and user.is_staff:
            request.session[PENDING_KEY] = user.pk
            request.session[NEXT_KEY] = _safe_next(request, request.POST.get("next"))
            request.session[ATTEMPTS_KEY] = 0
            if TOTPDevice.objects.filter(user=user, confirmed=True).exists():
                return redirect("accounts:otp")
            return redirect("accounts:otp_setup")
        error = "아이디 또는 비밀번호가 올바르지 않습니다."
    return render(
        request, "accounts/login.html", {"error": error, "next": request.GET.get("next", "")}
    )


def otp_view(request: HttpRequest) -> HttpResponse:
    user = _pending_user(request)
    if user is None:
        return redirect("accounts:login")
    device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
    if device is None:
        return redirect("accounts:otp_setup")
    error = ""
    if request.method == "POST":
        if device.verify(request.POST.get("code", "")):
            return _finish_login(request, user)
        if _count_failure(request):
            return redirect("accounts:login")
        error = WRONG_CODE
    return render(request, "accounts/otp.html", {"error": error})


def otp_setup_view(request: HttpRequest) -> HttpResponse:
    user = _pending_user(request)
    if user is None:
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
        if _count_failure(request):
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
