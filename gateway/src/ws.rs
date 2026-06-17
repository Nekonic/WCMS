//! WebSocket upgrade handler for `GET /ws`.
//!
//! # Per-connection lifecycle
//!
//! 1. Axum upgrades the HTTP connection to a WebSocket.
//! 2. The **first** inbound binary frame must be a `ClientEnvelope::Hello`.
//!    We parse the `client_id` UUID from it, register the client in the
//!    [`Registry`], and send back a `ServerEnvelope::Welcome`.
//! 3. A **writer task** is spawned; it drains the per-connection mpsc channel
//!    and writes each `ServerEnvelope` as a binary protobuf frame.
//! 4. The **read loop** decodes subsequent `ClientEnvelope` frames:
//!    - `Heartbeat`  → log + TODO forward to Django
//!    - `CommandAck` → log + TODO forward to Django
//!    - `CommandResult` → log + TODO forward to Django
//!    - `LogEvent`   → log + TODO forward to Django
//! 5. On socket close/error: `unregister` the client (presence = offline).
//!
//! Axum automatically replies to WebSocket `Ping` frames with `Pong`;
//! no manual ping handling is required for that path.  Periodic server-side
//! pings (to detect half-open connections) are a DEFERRED item — see TODO.
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
    proto::{
        client_envelope, server_envelope, ClientEnvelope, ServerEnvelope, Welcome,
    },
    registry::Registry,
};

/// Shared application state injected by axum.
#[derive(Clone)]
pub struct AppState {
    pub registry: Registry,
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

    // ── Step 3: Send Welcome ──────────────────────────────────────────────

    let welcome = build_welcome();
    if let Err(e) = send_envelope(&mut sink, welcome).await {
        error!(client_id = %client_id, "ws: failed to send Welcome: {e}");
        state.registry.unregister(client_id, &sender);
        return;
    }

    // ── Step 4: Spawn writer task ─────────────────────────────────────────

    let writer_handle = tokio::spawn(writer_task(sink, rx));

    // ── Step 5: Read loop ─────────────────────────────────────────────────

    while let Some(result) = stream.next().await {
        match result {
            Ok(msg) => {
                if !dispatch_client_message(client_id, msg) {
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

    // ── Step 6: Cleanup ───────────────────────────────────────────────────

    info!(client_id = %client_id, "ws: connection closed — unregistering (offline)");
    state.registry.unregister(client_id, &sender);

    // Abort the writer task; the mpsc receiver is dropped when this task
    // exits, which causes the writer to drain and exit cleanly.
    writer_handle.abort();
}

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

/// Dispatch a subsequent `ClientEnvelope` frame from the read loop.
///
/// Returns `false` if the connection should be closed (Close frame received).
fn dispatch_client_message(client_id: Uuid, msg: Message) -> bool {
    match msg {
        Message::Binary(bytes) => {
            match ClientEnvelope::decode(bytes.as_ref()) {
                Ok(envelope) => {
                    if let Some(payload) = envelope.payload {
                        handle_client_payload(client_id, payload);
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

fn handle_client_payload(client_id: Uuid, payload: client_envelope::Payload) {
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
            // TODO(django-integration): forward heartbeat telemetry to Django
            // internal API (POST /internal/telemetry/heartbeat).
        }
        client_envelope::Payload::CommandAck(ack) => {
            info!(
                client_id = %client_id,
                command_id = %ack.command_id,
                "ws: CommandAck received"
            );
            // TODO(django-integration): notify Django that the command was
            // received (transition: sent -> executing in commands table).
        }
        client_envelope::Payload::CommandResult(result) => {
            info!(
                client_id = %client_id,
                command_id = %result.command_id,
                status = ?result.status,
                exit_code = result.exit_code,
                "ws: CommandResult received"
            );
            // TODO(django-integration): POST result to Django internal API
            // (POST /internal/commands/{id}/result).
        }
        client_envelope::Payload::LogEvent(log) => {
            info!(
                client_id = %client_id,
                level = ?log.level,
                source = %log.source,
                message = %log.message,
                "ws: LogEvent received"
            );
            // TODO(django-integration): batch or immediately forward to Django
            // log ingestion endpoint.
        }
    }
}

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
