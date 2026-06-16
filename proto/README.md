# WCMS 와이어 스키마 (protobuf)

PC(C# 클라이언트) <-> Rust 실시간 게이트웨이 WebSocket 메시지의 단일 진실 소스.
설계: `../docs/REWRITE_DESIGN.md` 4.6. REST(enrollment/다운로드/로그 배치)는 여기 포함 안 함.

- `wcms/v1/common.proto` — 공용 enum (CommandType, CommandResultStatus, DeliveryMode, LogLevel)
- `wcms/v1/realtime.proto` — WS envelope + 메시지 (Hello, Welcome, Heartbeat, Command, CommandAck, CommandResult, LogEvent)

## 검증

```bash
protoc -I proto --descriptor_set_out=/dev/null proto/wcms/v1/*.proto
```

## 코드 생성

```bash
cd proto && buf generate    # ../gen/{csharp,rust,python} 에 생성 (빌드 산출물)
```
