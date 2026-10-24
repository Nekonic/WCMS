"""개발용 가짜 클라이언트. C++ 클라이언트 없이 서버와 화면을 확인할 때 쓴다. 프로토콜은 protocol/README.md.

uv run python tools/fake_client.py --server http://localhost:8000 --pin 123456 --count 8
"""

import argparse
import asyncio
import json
import random
import urllib.request
from pathlib import Path

import websockets

STATE_FILE = Path(__file__).with_name(".fake_clients.json")
CLOSE_REVOKED = 4410
APPS = [
    ("chrome.exe", "자료구조 3주차 - Google Docs - Chrome"),
    ("chrome.exe", "YouTube - Chrome"),
    ("Code.exe", "main.cpp - Visual Studio Code"),
    ("explorer.exe", "파일 탐색기"),
]


def load_tokens() -> dict[str, str]:
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}


def save_tokens(tokens: dict[str, str]) -> None:
    STATE_FILE.write_text(json.dumps(tokens))


def register(server: str, pin: str, index: int) -> str:
    body = json.dumps(
        {
            "pin": pin,
            "hostname": f"FAKE-{index:02d}",
            "machine_guid": f"fake-{index}",
            "specs": {"cpu": "Fake CPU", "ram_gb": 16, "os": "Windows 11"},
            "version": "2026.1",
        }
    ).encode()
    request = urllib.request.Request(
        f"{server}/client/register", data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(request) as response:
        return json.load(response)["token"]


def fake_status() -> dict:
    session = random.choices(["active", "locked", "none"], weights=[8, 1, 1])[0]
    process, title = random.choice(APPS)
    status = {
        "type": "status",
        "cpu": round(random.uniform(1, 60), 1),
        "mem_used": random.randint(4, 12) * 1024**3,
        "mem_total": 16 * 1024**3,
        "disk_used": 246 * 1000**3,
        "disk_total": 512 * 1000**3,
        "session": session,
        "user": "Student" if session != "none" else "",
    }
    if session == "active":
        status["foreground"] = {"process": process, "title": title}
    return status


async def run_one(ws_url: str, index: int, tokens: dict[str, str]) -> None:
    headers = {"Authorization": f"Bearer {tokens[str(index)]}"}
    async for ws in websockets.connect(ws_url, additional_headers=headers):
        try:
            await ws.send(json.dumps({"type": "hello", "proto": 1, "version": "2026.1"}))
            while True:
                await ws.send(json.dumps(fake_status()))
                await asyncio.sleep(10)
        except websockets.ConnectionClosed as closed:
            if closed.rcvd is not None and closed.rcvd.code == CLOSE_REVOKED:
                tokens.pop(str(index), None)
                save_tokens(tokens)
                print(f"FAKE-{index:02d}: 토큰이 무효가 되어 멈춥니다. --pin으로 다시 등록하세요.")
                return


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="http://localhost:8000")
    parser.add_argument("--pin")
    parser.add_argument("--count", type=int, default=8)
    args = parser.parse_args()
    server = args.server.rstrip("/")

    tokens = load_tokens()
    for index in range(1, args.count + 1):
        if str(index) not in tokens:
            if not args.pin:
                parser.error(f"FAKE-{index:02d}의 토큰이 없습니다. --pin을 주세요.")
            tokens[str(index)] = register(server, args.pin, index)
            save_tokens(tokens)

    ws_url = server.replace("http", "ws", 1) + "/client/ws"
    await asyncio.gather(*(run_one(ws_url, i, tokens) for i in range(1, args.count + 1)))


if __name__ == "__main__":
    asyncio.run(main())
