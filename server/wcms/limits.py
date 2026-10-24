from django.core.cache import cache


class FailureLimiter:
    """키별 실패 횟수를 센다. 창은 첫 실패 시점부터 고정되고 실패가 이어져도 늘어나지 않는다."""

    def __init__(self, name: str, limit: int, window: int):
        self.name = name
        self.limit = limit
        self.window = window

    def _key(self, ident: str) -> str:
        return f"fail:{self.name}:{ident}"

    def blocked(self, ident: str) -> bool:
        return cache.get(self._key(ident), 0) >= self.limit

    def record(self, ident: str) -> None:
        key = self._key(ident)
        cache.add(key, 0, self.window)
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, self.window)

    def reset(self, ident: str) -> None:
        cache.delete(self._key(ident))
