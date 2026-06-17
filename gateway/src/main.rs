//! WCMS realtime gateway — binary entry point.
//!
//! # Environment variables
//!
//! | Variable        | Default            | Description                  |
//! |─────────────────|────────────────────|──────────────────────────────|
//! | `GATEWAY_ADDR`  | `127.0.0.1:8080`   | TCP listen address           |
//! | `RUST_LOG`      | `info`             | tracing-subscriber log filter |

use std::{net::SocketAddr, sync::Arc};

use axum::{routing::get, Router};
use tracing::info;

use gateway::{
    registry::Registry,
    ws::{ws_handler, AppState},
};

#[tokio::main]
async fn main() {
    // ── Tracing ───────────────────────────────────────────────────────────
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "info".into()),
        )
        .init();

    // ── State ─────────────────────────────────────────────────────────────
    let state = Arc::new(AppState {
        registry: Registry::new(),
    });

    // ── Router ────────────────────────────────────────────────────────────
    let app = Router::new()
        .route("/ws", get(ws_handler))
        .route("/health", get(health_handler))
        .with_state(state);

    // ── Bind address ──────────────────────────────────────────────────────
    let addr: SocketAddr = std::env::var("GATEWAY_ADDR")
        .unwrap_or_else(|_| "127.0.0.1:8080".to_owned())
        .parse()
        .expect("GATEWAY_ADDR must be a valid socket address (e.g. 0.0.0.0:8080)");

    info!(%addr, "gateway listening");

    // ── Serve with graceful shutdown on Ctrl-C ────────────────────────────
    let listener = tokio::net::TcpListener::bind(addr)
        .await
        .expect("failed to bind TCP listener");

    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await
        .expect("server error");

    info!("gateway shut down cleanly");
}

async fn health_handler() -> &'static str {
    "ok"
}

async fn shutdown_signal() {
    tokio::signal::ctrl_c()
        .await
        .expect("failed to install CTRL+C handler");
    info!("shutdown signal received");
}
