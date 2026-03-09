import os
import requests
from typing import Any


def execute(data: dict[str, Any]) -> str:
    url = data.get('url', '')
    destination = data.get('destination')
    if not url:
        return "오류: url이 필요합니다."
    if destination:
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        save_path = destination
    else:
        filename = url.split('/')[-1] or 'downloaded_file'
        downloads = os.path.join(os.path.expanduser('~'), 'Downloads')
        os.makedirs(downloads, exist_ok=True)
        save_path = os.path.join(downloads, filename)
    response = requests.get(url, stream=True, timeout=60)
    response.raise_for_status()
    with open(save_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    return f"다운로드 완료: {save_path} ({os.path.getsize(save_path):,} bytes)"