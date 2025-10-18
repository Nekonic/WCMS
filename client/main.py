import time
import requests
from collector import collect_system_info

SERVER_URL = "http://10.211.55.2:5050/"
MACHINE_ID = "TEST-001"

def send_heartbeat():
    data = {
        "machine_id": MACHINE_ID,
        "system_info": collect_system_info()
    }
    print(collect_system_info())
    try:
        r = requests.post(f"{SERVER_URL}/api/client/heartbeat", json=data)
        print(f"Heartbeat 응답: {r.status_code} {r.json()}")
    except Exception as e:
        print(f"Heartbeat 오류: {e}")

if __name__ == "__main__":
    while True:
        send_heartbeat()
        time.sleep(6)
