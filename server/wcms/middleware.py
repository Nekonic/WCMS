from django.http import JsonResponse

from wcms.api import error_body
from wcms.net import is_internal_request


class InternalOnlyMiddleware:
    """클라이언트 경로(/client/)는 내부용 nginx 블록을 거친 요청만 받는다."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/client/") and not is_internal_request(request):
            return JsonResponse(error_body("not_found", "없는 경로입니다."), status=404)
        return self.get_response(request)
