# WCMS Realtime Gateway

Rust WebSocket server that is the **authoritative presence registry** for lab PCs.

One process holds all ~80 PC connections. Connected = online; disconnected = offline — event-driven, no timeout polling (design §4.1).

## Quick start

```bash
cd gateway

# Build
cargo build

# Run (default: 127.0.0.1:8080)
cargo run

# Custom bind address
GATEWAY_ADDR=0.0.0.0:9000 cargo run

# Run tests
cargo test
```

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /ws` | WebSocket upgrade. First binary frame must be a `ClientEnvelope::Hello`. |
| `GET /health` | Returns `200 ok`. Used by load-balancer / Docker health check. |

## Wire protocol

Binary protobuf over WebSocket binary frames. One frame = one envelope.

- **PC → gateway**: `ClientEnvelope` (Hello / Heartbeat / CommandAck / CommandResult / LogEvent)
- **gateway → PC**: `ServerEnvelope` (Welcome / Command)

Proto sources: `proto/wcms/v1/common.proto`, `proto/wcms/v1/realtime.proto`

## Module layout

```
gateway/
├── build.rs           prost-build: compiles proto/ -> OUT_DIR/wcms.v1.rs
├── src/
│   ├── main.rs        Binary: tracing init, axum router, graceful shutdown
│   ├── lib.rs         Library root exposing modules + proto codec tests
│   ├── proto.rs       include! generated code; re-exports for crate-wide use
│   ├── registry.rs    Registry: DashMap<Uuid, mpsc::Sender<ServerEnvelope>>
│   └── ws.rs          axum WS handler: handshake, writer task, read loop
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GATEWAY_ADDR` | `127.0.0.1:8080` | TCP listen address |
| `RUST_LOG` | `info` | tracing log filter (e.g. `gateway=debug`) |

## Deferred items (next phases)

- **mTLS client-cert auth** (design §4.2): verify TLS client certificate against `clients` table on every connection; reject revoked certs. Currently the gateway trusts any `client_id` in the Hello frame.
- **Django internal API — presence sink**: on connect/disconnect, POST to Django `/internal/presence/{client_id}/{online|offline}` so Django can persist `network_events` and update `is_online`.
- **Django internal API — command source**: expose an internal HTTP endpoint (e.g. `POST /internal/push/{client_id}`) so Django can push a `ServerEnvelope::Command` to a connected PC.
- **Django internal API — telemetry forwarding**: forward Heartbeat / CommandResult / CommandAck / LogEvent payloads to Django persistence endpoints.
- **Command delivery modes / queue drain** (design §4.4): on reconnect, ask Django for queued (`DELIVERY_MODE_QUEUE`) pending commands and push them before entering the normal read loop.
- **Periodic server-sent pings + missed-pong eviction** (design §4.1): send WS Ping frames every `ping_interval_sec`; track last-pong timestamp; after 2 missed pongs forcibly close and unregister the connection (detects half-open sockets ~30 s).
- **Prometheus metrics** (design §9): active connection count, frames in/out, push errors — expose at `GET /metrics`.
- **Docker / compose integration**: `Dockerfile` for the gateway binary, service entry in `docker-compose.yml`.
