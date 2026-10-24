#!/bin/sh
# 띄운 compose의 경로 규칙을 확인한다. 사용: deploy/smoke.sh [웹 https 주소] [클라이언트 주소] [웹 http 주소]
# 로컬 확인용 자체 서명 인증서도 받도록 curl -k 를 쓴다
set -u
WEB=${1:-https://localhost}
CLIENT=${2:-http://localhost:8889}
HTTP=${3:-http://localhost}
fail=0

check() {
    name=$1 expected=$2 actual=$3
    if [ "$expected" = "$actual" ]; then
        echo "ok   $name"
    else
        echo "FAIL $name: expected $expected, got $actual"
        fail=1
    fi
}

status() { curl -sk -o /dev/null -w '%{http_code}' "$@"; }
ctype() { curl -sk -o /dev/null -w '%{content_type}' "$@"; }

check "화면" 200 "$(status "$WEB/")"
check "화면 경로 fallback" 200 "$(status "$WEB/rooms/1")"
check "없는 /api 경로는 404" 404 "$(status "$WEB/api/nope")"
check "없는 /api 경로는 JSON" application/json "$(ctype "$WEB/api/nope" | cut -d';' -f1)"
check "/api 그 자체도 JSON 404" 404 "$(status "$WEB/api")"
check "로그인 상태" 200 "$(status "$WEB/api/auth/me")"
check "웹 블록의 /client 는 404" 404 "$(status -X POST "$WEB/client/register")"
check "X-WCMS-Via 위조도 404" 404 "$(status -X POST -H 'X-WCMS-Via: internal' "$WEB/client/register")"
check "/ws/live 업그레이드" 101 "$(curl -sk -o /dev/null -w '%{http_code}' -m 3 --http1.1 \
    -H 'Connection: Upgrade' -H 'Upgrade: websocket' -H 'Sec-WebSocket-Version: 13' \
    -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' -H "Origin: $WEB" "$WEB/ws/live")"
check "http는 https로 301" 301 "$(status "$HTTP/")"
check "클라이언트 블록의 등록은 Django까지 간다" 400 "$(status -X POST -H 'Content-Type: application/json' -d '{}' "$CLIENT/client/register")"
check "클라이언트 블록의 /api 는 404" 404 "$(status "$CLIENT/api/auth/me")"
check "클라이언트 블록 healthz" 200 "$(status "$CLIENT/healthz")"

exit $fail
