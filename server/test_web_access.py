import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def test_dashboard_access():
    """대시보드 GET 접근을 테스트합니다."""
    print("--- 1. Testing Dashboard Access (GET /) ---")
    try:
        response = requests.get(BASE_URL + "/", timeout=5)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Result: SUCCESS. Dashboard is accessible.\n")
        else:
            print(f"Result: FAILED. Server responded with error {response.status_code}. Check server logs.\n")
    except requests.exceptions.RequestException as e:
        print(f"Result: FAILED. Could not connect to server. Is it running? Error: {e}\n")

def test_layout_save():
    """레이아웃 저장 POST 접근을 테스트합니다."""
    print("--- 2. Testing Layout Save (POST /api/layout) ---")
    try:
        # 테스트용으로 보낼 간단한 레이아웃 데이터
        test_layout_data = {
            "TestLab": ["PC-01", "PC-02"]
        }
        headers = {'Content-Type': 'application/json'}

        response = requests.post(BASE_URL + "/api/layout", data=json.dumps(test_layout_data), headers=headers, timeout=5)

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            print("Result: SUCCESS. Layout saving API is working correctly.")
        elif response.status_code == 403:
            print("Result: FAILED (403 Forbidden). This is an access permission issue.")
            print("This is very likely caused by a CSRF (Cross-Site Request Forgery) protection mechanism.")
            print("Please check the Flask server's console output for any messages related to 'CSRF token missing'.")
        else:
            print(f"Result: FAILED. Server responded with an unexpected error code: {response.status_code}")
            print("Response body:", response.text)

    except requests.exceptions.RequestException as e:
        print(f"Result: FAILED. Could not connect to server. Is it running? Error: {e}")

if __name__ == "__main__":
    print("Starting server access tests...\n")
    test_dashboard_access()
    test_layout_save()
    print("\nTests finished.")
