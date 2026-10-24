from django.apps import AppConfig


class WcmsConfig(AppConfig):
    name = "wcms"

    def ready(self) -> None:
        # OpenAPI 인증 스키마 확장을 등록한다.
        from wcms import schema  # noqa: F401
