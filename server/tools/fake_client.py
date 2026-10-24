"""개발용 가짜 클라이언트. C++ 클라이언트 없이 서버 화면을 확인할 때 쓴다.

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
APPS = [
    ("chrome.exe", "자료구조 3주차 - Google Docs - Chrome"),
    ("chrome.exe", "YouTube - Chrome"),
    ("Code.exe", "main.cpp - Visual Studio Code"),
    ("explorer.exe", "파일 탐색기"),
]


def register(server: str, pin: str, index: int) -> str:
    body = json.dumps(
        {
            "pin": pin,
            "hostname": f"FAKE-{index:02d}",
            "machine_guid": f"fake-{index}",
            "specs": {"cpu": "Fake CPU", "ram_gb": 16},
            "version": "2026.1",
        }
    ).encode()
    request = urllib.request.Request(
        f"{server}/client/register",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        return json.load(response)["token"]


def fake_status() -> dict:
    session = random.choices(["active", "locked", "none"], weights=[8, 1, 1])[0]
    process, title = random.choice(APPS)
    return {
        "type": "status",
        "cpu": round(random.uniform(1, 60), 1),
        "mem_used": random.randint(4, 12) * 1024**3,
        "mem_total": 16 * 1024**3,
        "disk_used": 246 * 1000**3,
        "disk_total": 512 * 1000**3,
        "user": "Student" if session != "none" else "",
        "session": session,
        "foreground": {"process": process, "title": title} if session == "active" else None,
    }


async def run_one(ws_url: str, token: str) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    async for ws in websockets.connect(ws_url, additional_headers=headers):
        try:
            await ws.send(json.dumps({"type": "hello", "version": "2026.1"}))
            while True:
                await ws.send(json.dumps(fake_status()))
                await asyncio.sleep(10)
        except websockets.ConnectionClosed:
            continue


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="http://localhost:8000")
    parser.add_argument("--pin")
    parser.add_argument("--count", type=int, default=8)
    args = parser.parse_args()

    tokens: dict[str, str] = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    for index in range(1, args.count + 1):
        if str(index) not in tokens:
            if not args.pin:
                parser.error(f"FAKE-{index:02d}의 토큰이 없습니다. --pin을 주세요.")
            tokens[str(index)] = register(args.server, args.pin, index)
    STATE_FILE.write_text(json.dumps(tokens))

    ws_url = args.server.replace("http", "ws", 1) + "/client/ws"
    await asyncio.gather(*(run_one(ws_url, tokens[str(i)]) for i in range(1, args.count + 1)))


if __name__ == "__main__":
    asyncio.run(main())
