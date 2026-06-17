# WCMS Realtime Gateway

Rust WebSocket server that is the **authoritative presence registry** for lab PCs.

One process holds all ~80 PC connections. Connected = online; disconnected = offline — event-driven, no timeout polling (design §4.1).

## Quick start

```bash
cd gateway

# Build
cargo build

# Run (default: 127.0.0.1:8080)
WCMS_INTERNAL_TOKEN=<token> cargo run

# Custom bind address
GATEWAY_ADDR=0.0.0.0:9000 WCMS_INTERNAL_TOKEN=<token> cargo run

# Run tests
cargo test
```

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /ws` | WebSocket upgrade. First binary frame must be a `ClientEnvelope::Hello`. |
| `GET /health` | Returns `200 ok`. Used by load-balancer / Docker health check. |
| `POST /internal/push/{client_id}` | Django → gateway command push. Requires `Authorization: Bearer <WCMS_INTERNAL_TOKEN>`. Body: `{id, command_type, parameters, timeout_seconds, priority, delivery_mode?}`. Returns `{"delivered": true}` (200) if online, `{"delivered": false}` (404) if offline, `{"error": "Unauthorized"}` (401) if bad token. |

## Wire protocol

Binary protobuf over WebSocket binary frames. One frame = one envelope.

- **PC → gateway**: `ClientEnvelope` (Hello / Heartbeat / CommandAck / CommandResult / LogEvent)
- **gateway → PC**: `ServerEnvelope` (Welcome / Command)

Proto sources: `proto/wcms/v1/common.proto`, `proto/wcms/v1/realtime.proto`

## Gateway ↔ Django flows (Phase 2)

All Django calls use `Authorization: Bearer <WCMS_INTERNAL_TOKEN>` and are **non-fatal** — Django being down logs a warning and does not crash the WS connection.

| Event | Gateway action |
|-------|---------------|
| PC connects (Hello) | `POST /internal/presence/` `{event:"connect"}` |
| PC connects (Hello) | `GET /internal/clients/<id>/pending-commands/` → push each as `ServerEnvelope::Command` (queue drain, design §4.4) |
| PC sends Heartbeat | `POST /internal/telemetry/heartbeat/` |
| PC sends CommandAck | `POST /internal/telemetry/command-ack/` |
| PC sends CommandResult | `POST /internal/telemetry/command-result/` |
| PC sends LogEvent | tracing log only (see deferred: log sink) |
| PC disconnects | `POST /internal/presence/` `{event:"disconnect"}` (via RAII guard, all exit paths) |
| Django pushes command | `POST /internal/push/<client_id>` → `Registry::push` → WS frame |

## Module layout

```
gateway/
├── build.rs           prost-build: compiles proto/ -> OUT_DIR/wcms.v1.rs
├── src/
│   ├── main.rs        Binary: tracing init, axum router, graceful shutdown
│   ├── lib.rs         Library root exposing modules + proto codec tests
│   ├── proto.rs       include! generated code; re-exports for crate-wide use
│   ├── registry.rs    Registry: DashMap<Uuid, mpsc::Sender<ServerEnvelope>>
│   ├── ws.rs          axum WS handler: handshake, writer task, read loop, DisconnectGuard
│   ├── django.rs      DjangoClient: async HTTP calls to Django internal API
│   └── push.rs        POST /internal/push/{client_id} — Django → PC command delivery
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GATEWAY_ADDR` | `127.0.0.1:8080` | TCP listen address |
| `WCMS_DJANGO_URL` | `http://127.0.0.1:8000` | Django internal API base URL |
| `WCMS_INTERNAL_TOKEN` | — | Shared Bearer token for gateway↔Django auth (required in production) |
| `RUST_LOG` | `info` | tracing log filter (e.g. `gateway=debug`) |

## Deferred items (next phases)

- **mTLS client-cert auth** (design §4.2): verify TLS client certificate against `clients` table on every connection; reject revoked certs. Currently the gateway trusts any `client_id` in the Hello frame.
- **Django-side trigger to call `/internal/push`**: Django needs to call `POST <GATEWAY_URL>/internal/push/<client_id>` when it creates a new command for an online PC. The push endpoint contract is ready; the Django trigger is not yet wired.
- **Log sink**: `LogEvent` frames are currently only written to the tracing log. Once `POST /internal/telemetry/logs/` is implemented on the Django side, add the forward call in `ws.rs` (marked with `TODO(log-sink)`).
- **Periodic server-sent pings + missed-pong eviction** (design §4.1): send WS Ping frames every `ping_interval_sec`; track last-pong timestamp; after 2 missed pongs forcibly close and unregister the connection (detects half-open sockets ~30 s). Marked `TODO(phase-3)` in ws.rs.
- **Prometheus metrics** (design §9): active connection count, frames in/out, push errors — expose at `GET /metrics`.
- **Docker / compose integration**: `Dockerfile` for the gateway binary, service entry in `docker-compose.yml`.
