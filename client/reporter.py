"""명령 실행 결과를 서버로 전송하는 헬퍼."""
from typing import Any

import requests


def report_result(
    server_url: str,
    command_id: int,
    machine_id: str,
    status: str,
    result: Any = None,
    error: str | None = None,
) -> None:
    """명령 결과를 POST /api/client/commands/:id/result 로 전송."""
    try:
        requests.post(
            f'{server_url}/api/client/commands/{command_id}/result',
            json={
                'machine_id': machine_id,
                'status': status,
                'result': str(result) if result is not None else None,
                'error': error,
            },
            timeout=10,
        )
    except Exception:
        pass  # 결과 전송 실패는 무시