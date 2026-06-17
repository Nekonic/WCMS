//! 게이트웨이 내부 Push 엔드포인트 — `POST /internal/push/{client_id}`.
//!
//! Django 가 PC 에 명령을 전달할 때 이 엔드포인트를 호출한다.
//! 요청 헤더에 `Authorization: Bearer <WCMS_INTERNAL_TOKEN>` 이 있어야 한다.
//!
//! # 응답
//!
//! | 상황                          | 코드 | 본문                        |
//! |-------------------------------|------|-----------------------------|
//! | 클라이언트 온라인, 전송 성공  | 200  | `{"delivered": true}`       |
//! | 클라이언트 오프라인           | 404  | `{"delivered": false}`      |
//! | 인증 헤더 누락/불일치         | 401  | `{"error": "Unauthorized"}` |

use std::sync::Arc;

use axum::{
    extract::{Path, State},
    http::{HeaderMap, StatusCode},
    response::IntoResponse,
    Json,
};
use serde::Deserialize;
use serde_json::json;
use tracing::{info, warn};
use uuid::Uuid;

use crate::{
    django::{json_object_to_prost_struct, command_type_from_str},
    proto::{server_envelope, Command, DeliveryMode, ServerEnvelope},
    ws::AppState,
};

// ─── 요청 / 응답 DTO ──────────────────────────────────────────────────────────

/// Django 가 보내는 명령 Push 요청 본문.
#[derive(Debug, Deserialize)]
pub struct PushRequest {
    pub id: String,
    pub command_type: String,
    #[serde(default)]
    pub parameters: serde_json::Value,
    pub timeout_seconds: u32,
    pub priority: u32,
    #[serde(default)]
    pub delivery_mode: Option<String>,
}

// ─── 핸들러 ──────────────────────────────────────────────────────────────────

/// `POST /internal/push/{client_id}` 핸들러.
///
/// Bearer 토큰 검증 후 Registry 에서 해당 클라이언트를 찾아
/// `ServerEnvelope::Command` 를 push 한다.
pub async fn push_handler(
    headers: HeaderMap,
    Path(client_id): Path<Uuid>,
    State(state): State<Arc<AppState>>,
    Json(body): Json<PushRequest>,
) -> impl IntoResponse {
    // ── 인증 ────────────────────────────────────────────────────────────
    // AppState 에 저장된 토큰과 비교한다 (env 직접 읽기 금지 — 테스트 race-free).
    let expected_token = &state.internal_token;
    let provided = headers
        .get("Authorization")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("");

    let expected_bearer = format!("Bearer {expected_token}");
    if provided != expected_bearer || expected_token.is_empty() {
        warn!(
            client_id = %client_id,
            "push: 인증 실패 — 잘못된 Authorization 헤더"
        );
        return (
            StatusCode::UNAUTHORIZED,
            Json(json!({"error": "Unauthorized"})),
        );
    }

    // ── Command 구성 ─────────────────────────────────────────────────────
    let cmd_type = command_type_from_str(&body.command_type);

    let parameters = if body.parameters.is_null() || body.parameters == serde_json::Value::Null {
        None
    } else {
        Some(json_object_to_prost_struct(body.parameters))
    };

    let delivery_mode = match body.delivery_mode.as_deref() {
        Some("queue") => DeliveryMode::Queue,
        Some("drop_if_offline") => DeliveryMode::DropIfOffline,
        _ => DeliveryMode::DropIfOffline, // 기본값: 오프라인이면 폐기
    };

    let envelope = ServerEnvelope {
        payload: Some(server_envelope::Payload::Command(Command {
            id: body.id.clone(),
            r#type: cmd_type as i32,
            parameters,
            timeout_sec: body.timeout_seconds,
            priority: body.priority,
            created_at: None, // Django 가 보내지 않으면 None
            delivery_mode: delivery_mode as i32,
        })),
    };

    // ── Registry push ────────────────────────────────────────────────────
    if state.registry.push(client_id, envelope) {
        info!(
            client_id = %client_id,
            command_id = %body.id,
            command_type = %body.command_type,
            "push: 명령 전달 성공"
        );
        (StatusCode::OK, Json(json!({"delivered": true})))
    } else {
        warn!(
            client_id = %client_id,
            command_id = %body.id,
            "push: 클라이언트 오프라인 — 명령 폐기"
        );
        (StatusCode::NOT_FOUND, Json(json!({"delivered": false})))
    }
}

// ─── 단위 테스트 ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{
        body::Body,
        http::Request,
        routing::post,
        Router,
    };
    use http_body_util::BodyExt;
    use tower::util::ServiceExt;

    use crate::{
        django::DjangoClient,
        registry::Registry,
        ws::AppState,
    };

    /// 테스트용 axum 앱을 생성한다.
    fn make_app(token: &str, registry: Registry) -> Router {
        let state = Arc::new(AppState {
            registry,
            django: Arc::new(DjangoClient::new("http://127.0.0.1:19999", token)),
            internal_token: token.to_owned(),
        });

        Router::new()
            .route("/internal/push/:client_id", post(push_handler))
            .with_state(state)
    }

    #[tokio::test]
    async fn push_delivers_command_to_online_client() {
        let token = "secret-push-token";
        let registry = Registry::new();
        let client_id = Uuid::new_v4();

        // 클라이언트 등록 (온라인 상태 시뮬레이션)
        let mut rx = registry.register(client_id);

        let app = make_app(token, registry);

        let body = json!({
            "id": "cmd-test-001",
            "command_type": "shutdown",
            "parameters": {"delay_sec": 10},
            "timeout_seconds": 60,
            "priority": 1
        });

        let req = Request::builder()
            .method("POST")
            .uri(format!("/internal/push/{client_id}"))
            .header("Content-Type", "application/json")
            .header("Authorization", format!("Bearer {token}"))
            .body(Body::from(body.to_string()))
            .unwrap();

        let resp = app
            .into_service()
            .oneshot(req)
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::OK);

        let bytes = resp.into_body().collect().await.unwrap().to_bytes();
        let json_resp: serde_json::Value = serde_json::from_slice(&bytes).unwrap();
        assert_eq!(json_resp["delivered"], true);

        // 채널에서 수신된 ServerEnvelope 확인
        let envelope = rx.try_recv().expect("envelope 이 채널에 있어야 한다");
        match envelope.payload {
            Some(server_envelope::Payload::Command(cmd)) => {
                assert_eq!(cmd.id, "cmd-test-001");
                assert_eq!(cmd.r#type, crate::proto::CommandType::Shutdown as i32);
                assert_eq!(cmd.timeout_sec, 60);
                assert_eq!(cmd.priority, 1);
            }
            other => panic!("Command payload 가 아님: {other:?}"),
        }
    }

    #[tokio::test]
    async fn push_returns_404_for_offline_client() {
        let token = "secret-push-token-404";
        let registry = Registry::new();
        let offline_client_id = Uuid::new_v4();
        // 등록하지 않음 → 오프라인

        let app = make_app(token, registry);

        let body = json!({
            "id": "cmd-offline-001",
            "command_type": "message",
            "parameters": {},
            "timeout_seconds": 30,
            "priority": 0
        });

        let req = Request::builder()
            .method("POST")
            .uri(format!("/internal/push/{offline_client_id}"))
            .header("Content-Type", "application/json")
            .header("Authorization", format!("Bearer {token}"))
            .body(Body::from(body.to_string()))
            .unwrap();

        let resp = app
            .into_service()
            .oneshot(req)
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::NOT_FOUND);

        let bytes = resp.into_body().collect().await.unwrap().to_bytes();
        let json_resp: serde_json::Value = serde_json::from_slice(&bytes).unwrap();
        assert_eq!(json_resp["delivered"], false);
    }

    #[tokio::test]
    async fn push_returns_401_for_wrong_token() {
        let token = "correct-token-401";
        let registry = Registry::new();
        let client_id = Uuid::new_v4();
        let _rx = registry.register(client_id);

        let app = make_app(token, registry);

        let body = json!({
            "id": "cmd-auth-test",
            "command_type": "restart",
            "parameters": {},
            "timeout_seconds": 30,
            "priority": 0
        });

        let req = Request::builder()
            .method("POST")
            .uri(format!("/internal/push/{client_id}"))
            .header("Content-Type", "application/json")
            .header("Authorization", "Bearer wrong-token")
            .body(Body::from(body.to_string()))
            .unwrap();

        let resp = app
            .into_service()
            .oneshot(req)
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::UNAUTHORIZED);
    }
}
