from django.conf import settings
from django.http import HttpRequest


def version(request: HttpRequest) -> dict[str, str]:
    return {"wcms_version": settings.WCMS_VERSION}
