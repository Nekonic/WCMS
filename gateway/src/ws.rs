//! WebSocket upgrade handler for `GET /ws`.
//!
//! # Per-connection lifecycle
//!
//! 1. Axum upgrades the HTTP connection to a WebSocket.
//! 2. The **first** inbound binary frame must be a `ClientEnvelope::Hello`.
//!    We parse the `client_id` UUID from it, register the client in the
//!    [`Registry`], and send back a `ServerEnvelope::Welcome`.
//! 3. On Hello: Django `presence(connect=true)` + fetch_pending_commands 호출.
//!    대기 중인 명령을 모두 클라이언트에 push 한다 (design §4.4 큐 드레인).
//! 4. A **writer task** is spawned; it drains the per-connection mpsc channel
//!    and writes each `ServerEnvelope` as a binary protobuf frame.
//! 5. The **read loop** decodes subsequent `ClientEnvelope` frames:
//!    - `Heartbeat`     → Django heartbeat 텔레메트리 전송
//!    - `CommandAck`    → Django command-ack 전송
//!    - `CommandResult` → Django command-result 전송
//!    - `LogEvent`      → tracing 로그 + TODO(log-sink)
//! 6. On socket close/error: `unregister` + Django `presence(connect=false)`.
//!    DisconnectGuard 로 모든 종료 경로에서 실행을 보장한다.
//!
//! # Anti-pattern guard (design §5)
//! No blocking calls (`std::thread::sleep`, sync I/O) are used inside any
//! async task.  All I/O goes through `tokio`/`axum`.

use std::sync::Arc;

use axum::{
    extract::{
        ws::{Message, WebSocket, WebSocketUpgrade},
        State,
    },
    response::IntoResponse,
};
use futures::{SinkExt, StreamExt};
use prost::Message as ProstMessage;
use prost_types::Timestamp;
use tokio::sync::mpsc;
use tracing::{error, info, warn};
use uuid::Uuid;

use crate::{
    django::{pending_command_to_proto, DjangoClient},
    proto::{
        client_envelope, server_envelope, ClientEnvelope, ServerEnvelope, Welcome,
    },
    registry::Registry,
};

/// Shared application state injected by axum.
#[derive(Clone)]
pub struct AppState {
    pub registry: Registry,
    pub django: Arc<DjangoClient>,
    /// `WCMS_INTERNAL_TOKEN` — 게이트웨이 내부 API 인증에 사용된다.
    /// push 핸들러가 env 대신 여기서 읽으므로 테스트에서 race-free 하다.
    pub internal_token: String,
}

/// axum route handler for `GET /ws`.
pub async fn ws_handler(
    ws: WebSocketUpgrade,
    State(state): State<Arc<AppState>>,
) -> impl IntoResponse {
    ws.on_upgrade(move |socket| handle_socket(socket, state))
}

// ─── Internal ────────────────────────────────────────────────────────────────

async fn handle_socket(socket: WebSocket, state: Arc<AppState>) {
    let (mut sink, mut stream) = socket.split();

    // ── Step 1: Read the mandatory Hello frame ────────────────────────────

    let hello_msg = match stream.next().await {
        Some(Ok(msg)) => msg,
        Some(Err(e)) => {
            warn!("ws: error before Hello: {e}");
            return;
        }
        None => {
            warn!("ws: connection closed before Hello");
            return;
        }
    };

    let (client_id, _client_version) = match parse_hello(hello_msg) {
        Some(v) => v,
        None => {
            warn!("ws: first frame was not a valid Hello — closing");
            return;
        }
    };

    info!(client_id = %client_id, "ws: Hello received — client connected");

    // ── Step 2: Register client and obtain the outbound receiver ─────────

    let rx = state.registry.register(client_id);
    // Clone the sender so we can compare it during unregister.
    let sender = state
        .registry
        .sender(client_id)
        .expect("sender must exist immediately after register");

    // ── Step 3: Django presence(connect) + 큐 드레인 ─────────────────────

    // presence(connect=true) — Django 장애 시 warn 후 계속 진행
    if let Err(e) = state.django.presence(client_id, true).await {
        warn!(client_id = %client_id, error = %e, "ws: Django presence(connect) 실패 — 무시");
    }

    // 재연결 시 대기 중인 명령 fetch → push (design §4.4)
    match state.django.fetch_pending_commands(client_id).await {
        Ok(pending) => {
            for cmd in pending {
                let proto_cmd = pending_command_to_proto(cmd);
                let envelope = ServerEnvelope {
                    payload: Some(server_envelope::Payload::Command(proto_cmd)),
                };
                // Registry 에 직접 push; writer_task 가 아직 시작 전이므로
                // send_envelope 를 직접 호출한다.
                if let Err(e) = send_envelope(&mut sink, envelope).await {
                    error!(client_id = %client_id, "ws: 대기 명령 전송 실패: {e}");
                    state.registry.unregister(client_id, &sender);
                    // presence disconnect 도 알린다
                    if let Err(de) = state.django.presence(client_id, false).await {
                        warn!(client_id = %client_id, error = %de, "ws: Django presence(disconnect) 실패 — 무시");
                    }
                    return;
                }
            }
        }
        Err(e) => {
            warn!(client_id = %client_id, error = %e, "ws: pending-commands fetch 실패 — 무시");
        }
    }

    // ── Step 4: Send Welcome ──────────────────────────────────────────────

    let welcome = build_welcome();
    if let Err(e) = send_envelope(&mut sink, welcome).await {
        error!(client_id = %client_id, "ws: failed to send Welcome: {e}");
        state.registry.unregister(client_id, &sender);
        if let Err(de) = state.django.presence(client_id, false).await {
            warn!(client_id = %client_id, error = %de, "ws: Django presence(disconnect) 실패 — 무시");
        }
        return;
    }

    // ── Step 5: Spawn writer task ─────────────────────────────────────────

    let writer_handle = tokio::spawn(writer_task(sink, rx));

    // ── Step 6: Read loop ─────────────────────────────────────────────────

    // DisconnectGuard: 모든 종료 경로에서 presence(disconnect) + unregister 를 보장한다.
    let guard = DisconnectGuard {
        client_id,
        sender: sender.clone(),
        registry: state.registry.clone(),
        django: state.django.clone(),
    };

    while let Some(result) = stream.next().await {
        match result {
            Ok(msg) => {
                if !dispatch_client_message(client_id, msg, &state.django).await {
                    // Socket closed gracefully.
                    break;
                }
            }
            Err(e) => {
                warn!(client_id = %client_id, "ws: read error: {e}");
                break;
            }
        }
    }

    // ── Step 7: Cleanup ───────────────────────────────────────────────────

    info!(client_id = %client_id, "ws: connection closed — unregistering (offline)");
    // guard 가 Drop 될 때 unregister + Django presence(disconnect) 를 호출한다.
    drop(guard);

    // Abort the writer task; the mpsc receiver is dropped when this task
    // exits, which causes the writer to drain and exit cleanly.
    writer_handle.abort();
}

// ─── DisconnectGuard ─────────────────────────────────────────────────────────

/// RAII guard: 소켓 종료 시(정상/오류/panic 모두) unregister + Django disconnect 를 보장.
struct DisconnectGuard {
    client_id: Uuid,
    sender: mpsc::Sender<ServerEnvelope>,
    registry: Registry,
    django: Arc<DjangoClient>,
}

impl Drop for DisconnectGuard {
    fn drop(&mut self) {
        self.registry.unregister(self.client_id, &self.sender);

        // Drop 내에서는 async fn 을 직접 await 할 수 없다.
        // tokio::spawn 으로 별도 task 에서 비동기 호출을 수행한다.
        let django = self.django.clone();
        let client_id = self.client_id;
        tokio::spawn(async move {
            if let Err(e) = django.presence(client_id, false).await {
                warn!(client_id = %client_id, error = %e, "ws: Django presence(disconnect) 실패 — 무시");
            }
        });
    }
}

// ─── Writer task ─────────────────────────────────────────────────────────────

/// Drain the per-connection mpsc channel and write each `ServerEnvelope` as a
/// binary protobuf frame.  Exits when the channel is closed (which happens when
/// the read loop drops the `Registry` entry).
async fn writer_task(
    mut sink: futures::stream::SplitSink<WebSocket, Message>,
    mut rx: mpsc::Receiver<ServerEnvelope>,
) {
    while let Some(envelope) = rx.recv().await {
        if let Err(e) = send_envelope(&mut sink, envelope).await {
            warn!("ws writer: send error: {e} — exiting writer task");
            break;
        }
    }
}

/// Encode `envelope` as binary protobuf and send it as one WS binary frame.
async fn send_envelope(
    sink: &mut futures::stream::SplitSink<WebSocket, Message>,
    envelope: ServerEnvelope,
) -> Result<(), axum::Error> {
    let mut buf = Vec::new();
    envelope
        .encode(&mut buf)
        .expect("protobuf encode is infallible for valid messages");
    sink.send(Message::Binary(buf.into())).await
}

// ─── Handshake helpers ───────────────────────────────────────────────────────

/// Try to decode a `ClientEnvelope::Hello` from a WS message.
///
/// Returns `(client_id, client_version)` on success.
fn parse_hello(msg: Message) -> Option<(Uuid, String)> {
    let bytes = match msg {
        Message::Binary(b) => b,
        // Ignore text/ping/pong/close during the handshake.
        _ => return None,
    };

    let envelope = ClientEnvelope::decode(bytes.as_ref()).ok()?;
    match envelope.payload? {
        client_envelope::Payload::Hello(hello) => {
            let client_id = Uuid::parse_str(&hello.client_id).ok()?;
            Some((client_id, hello.client_version))
        }
        _ => None,
    }
}

// ─── Dispatch ────────────────────────────────────────────────────────────────

/// Dispatch a subsequent `ClientEnvelope` frame from the read loop.
///
/// Returns `false` if the connection should be closed (Close frame received).
async fn dispatch_client_message(
    client_id: Uuid,
    msg: Message,
    django: &DjangoClient,
) -> bool {
    match msg {
        Message::Binary(bytes) => {
            match ClientEnvelope::decode(bytes.as_ref()) {
                Ok(envelope) => {
                    if let Some(payload) = envelope.payload {
                        handle_client_payload(client_id, payload, django).await;
                    }
                }
                Err(e) => {
                    warn!(client_id = %client_id, "ws: failed to decode ClientEnvelope: {e}");
                }
            }
            true
        }
        Message::Ping(_) => {
            // axum replies automatically; nothing to do.
            true
        }
        Message::Pong(_) => {
            // TODO(phase-3): record last-pong timestamp for half-open detection.
            true
        }
        Message::Close(_) => {
            info!(client_id = %client_id, "ws: Close frame received");
            false
        }
        Message::Text(_) => {
            warn!(client_id = %client_id, "ws: unexpected text frame — ignoring");
            true
        }
    }
}

async fn handle_client_payload(
    client_id: Uuid,
    payload: client_envelope::Payload,
    django: &DjangoClient,
) {
    match payload {
        client_envelope::Payload::Hello(_) => {
            // Duplicate Hello after handshake; ignore.
            warn!(client_id = %client_id, "ws: unexpected Hello after handshake — ignoring");
        }
        client_envelope::Payload::Heartbeat(hb) => {
            info!(
                client_id = %client_id,
                cpu = hb.cpu_usage,
                ram_pct = hb.ram_usage_percent,
                full = hb.full,
                "ws: Heartbeat received"
            );
            if let Err(e) = django.heartbeat(client_id, &hb).await {
                warn!(client_id = %client_id, error = %e, "ws: heartbeat Django 전송 실패 — 무시");
            }
        }
        client_envelope::Payload::CommandAck(ack) => {
            info!(
                client_id = %client_id,
                command_id = %ack.command_id,
                "ws: CommandAck received"
            );
            if let Err(e) = django.command_ack(&ack.command_id).await {
                warn!(client_id = %client_id, error = %e, "ws: command_ack Django 전송 실패 — 무시");
            }
        }
        client_envelope::Payload::CommandResult(result) => {
            info!(
                client_id = %client_id,
                command_id = %result.command_id,
                status = ?result.status,
                exit_code = result.exit_code,
                "ws: CommandResult received"
            );
            if let Err(e) = django.command_result(&result).await {
                warn!(client_id = %client_id, error = %e, "ws: command_result Django 전송 실패 — 무시");
            }
        }
        client_envelope::Payload::LogEvent(log) => {
            info!(
                client_id = %client_id,
                level = ?log.level,
                source = %log.source,
                message = %log.message,
                "ws: LogEvent received"
            );
            // TODO(log-sink): Django 측 로그 배치 수집 엔드포인트가 구현되면
            // POST /internal/telemetry/logs/ 로 전송한다.
            // 현재는 tracing 으로만 기록하고 끝낸다.
        }
    }
}

// ─── Welcome builder ─────────────────────────────────────────────────────────

fn build_welcome() -> ServerEnvelope {
    use std::time::{SystemTime, UNIX_EPOCH};

    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default();

    ServerEnvelope {
        payload: Some(server_envelope::Payload::Welcome(Welcome {
            server_time: Some(Timestamp {
                seconds: now.as_secs() as i64,
                nanos: now.subsec_nanos() as i32,
            }),
            ping_interval_sec: 15,
        })),
    }
}
