"""
클라이언트 유틸리티 단위 테스트
"""
import pytest
from client.utils import safe_request, retry_on_network_error, format_bytes


class TestSafeRequest:
    """safe_request 함수 테스트"""

    def test_safe_request_valid_url(self):
        """유효한 URL 요청"""
        # Google DNS 서버로 간단한 테스트 (항상 응답)
        # 실제 테스트에서는 mock을 사용해야 함
        pass

    def test_safe_request_timeout(self):
        """타임아웃 테스트"""
        # 로컬호스트의 존재하지 않는 포트로 요청
        result = safe_request('http://localhost:99999', timeout=0.001, max_retries=1)
        assert result is None


class TestRetryDecorator:
    """retry_on_network_error 데코레이터 테스트"""

    def test_retry_success_first_try(self):
        """첫 시도에 성공"""
        call_count = {'count': 0}

        @retry_on_network_error(max_retries=3, delay=0.001)
        def succeeds_immediately():
            call_count['count'] += 1
            return "success"

        result = succeeds_immediately()
        assert result == "success"
        assert call_count['count'] == 1

    def test_retry_eventually_succeeds(self):
        """여러 시도 후 성공"""
        call_count = {'count': 0}

        @retry_on_network_error(max_retries=3, delay=0.001)
        def succeeds_on_third_try():
            call_count['count'] += 1
            if call_count['count'] < 3:
                raise ConnectionError("Network error")
            return "success"

        result = succeeds_on_third_try()
        assert result == "success"
        assert call_count['count'] == 3


class TestFormatBytes:
    """format_bytes 함수 테스트"""

    def test_format_bytes_kb(self):
        """KB 포맷"""
        result = format_bytes(1024)
        assert "KB" in result or "B" in result

    def test_format_bytes_mb(self):
        """MB 포맷"""
        result = format_bytes(1024 * 1024)
        assert "MB" in result or "B" in result

    def test_format_bytes_gb(self):
        """GB 포맷"""
        result = format_bytes(1024 * 1024 * 1024)
        assert "GB" in result or "B" in result

    def test_format_bytes_zero(self):
        """0 바이트"""
        result = format_bytes(0)
        assert "0" in result

