//! Django 내부 API 클라이언트 (design §3, Phase 2).
//!
//! [`DjangoClient`]는 게이트웨이와 Django 사이의 stateless HTTP 경계를 담당한다.
//! 모든 메서드는 async이며 실패해도 에러를 반환(non-fatal) — 호출 측에서 warn!
//! 후 무시하는 것이 기본 정책이다.
//!
//! # 환경 변수
//!
//! | 변수                  | 기본값                    | 설명                         |
//! |-----------------------|--------------------------|------------------------------|
//! | `WCMS_DJANGO_URL`     | `http://127.0.0.1:8000`  | Django base URL              |
//! | `WCMS_INTERNAL_TOKEN` | —                        | Bearer 토큰 (필수)           |

use anyhow::{Context, Result};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use tracing::warn;

use crate::proto::{
    CommandResult, CommandResultStatus, Heartbeat,
};

// ─── 환경 변수 기본값 ─────────────────────────────────────────────────────────

const DEFAULT_DJANGO_URL: &str = "http://127.0.0.1:8000";

// ─── DjangoClient ─────────────────────────────────────────────────────────────

/// Django 내부 API 에 대한 비동기 HTTP 클라이언트.
///
/// `Arc<DjangoClient>` 로 axum 상태(State)에 삽입하여 모든 WS 핸들러에서 공유한다.
#[derive(Clone, Debug)]
pub struct DjangoClient {
    http: Client,
    base_url: String,
    token: String,
}

impl DjangoClient {
    /// 환경 변수에서 설정을 읽어 클라이언트를 생성한다.
    ///
    /// `WCMS_INTERNAL_TOKEN` 이 없으면 빈 문자열을 사용하며, 모든 요청은
    /// 401 Unauthorized 로 거부된다(운영 환경에서는 반드시 설정해야 한다).
    pub fn from_env() -> Self {
        let base_url = std::env::var("WCMS_DJANGO_URL")
            .unwrap_or_else(|_| DEFAULT_DJANGO_URL.to_owned());
        let token = std::env::var("WCMS_INTERNAL_TOKEN").unwrap_or_default();

        if token.is_empty() {
            warn!("WCMS_INTERNAL_TOKEN 이 설정되지 않았습니다 — Django API 호출이 모두 401 실패합니다");
        }

        Self::new(base_url, token)
    }

    /// 직접 base_url/token 을 지정해 클라이언트를 생성한다 (테스트에서 주로 사용).
    pub fn new(base_url: impl Into<String>, token: impl Into<String>) -> Self {
        let http = Client::builder()
            .use_rustls_tls()
            .build()
            .expect("reqwest::Client 생성 실패");

        Self {
            http,
            base_url: base_url.into(),
            token: token.into(),
        }
    }

    // ─── 헬퍼 ────────────────────────────────────────────────────────────────

    fn bearer(&self) -> String {
        format!("Bearer {}", self.token)
    }

    fn url(&self, path: &str) -> String {
        format!("{}{}", self.base_url, path)
    }

    // ─── Presence ────────────────────────────────────────────────────────────

    /// POST /internal/presence/  {client_id, event:"connect"|"disconnect"}
    pub async fn presence(&self, client_id: uuid::Uuid, connect: bool) -> Result<()> {
        #[derive(Serialize)]
        struct Body<'a> {
            client_id: &'a str,
            event: &'a str,
        }

        let client_id_str = client_id.to_string();
        let body = Body {
            client_id: &client_id_str,
            event: if connect { "connect" } else { "disconnect" },
        };

        let resp = self
            .http
            .post(self.url("/internal/presence/"))
            .header("Authorization", self.bearer())
            .json(&body)
            .send()
            .await
            .context("presence 요청 전송 실패")?;

        if !resp.status().is_success() {
            let status = resp.status();
            let text = resp.text().await.unwrap_or_default();
            anyhow::bail!("presence 응답 오류 {status}: {text}");
        }

        Ok(())
    }

    // ─── Heartbeat ───────────────────────────────────────────────────────────

    /// POST /internal/telemetry/heartbeat/
    ///
    /// proto [`Heartbeat`] 를 JSON body 로 변환한다.
    pub async fn heartbeat(&self, client_id: uuid::Uuid, hb: &Heartbeat) -> Result<()> {
        let body = heartbeat_to_json(client_id, hb);

        let resp = self
            .http
            .post(self.url("/internal/telemetry/heartbeat/"))
            .header("Authorization", self.bearer())
            .json(&body)
            .send()
            .await
            .context("heartbeat 요청 전송 실패")?;

        if !resp.status().is_success() {
            let status = resp.status();
            let text = resp.text().await.unwrap_or_default();
            anyhow::bail!("heartbeat 응답 오류 {status}: {text}");
        }

        Ok(())
    }

    // ─── CommandResult ───────────────────────────────────────────────────────

    /// POST /internal/telemetry/command-result/
    pub async fn command_result(
        &self,
        result: &CommandResult,
    ) -> Result<()> {
        #[derive(Serialize)]
        struct Body<'a> {
            command_id: &'a str,
            status: &'a str,
            #[serde(skip_serializing_if = "Option::is_none")]
            output: Option<&'a str>,
            #[serde(skip_serializing_if = "Option::is_none")]
            error_message: Option<&'a str>,
            #[serde(skip_serializing_if = "Option::is_none")]
            exit_code: Option<i32>,
        }

        let status_str = command_result_status_str(result.status);

        let output = if result.output.is_empty() {
            None
        } else {
            Some(result.output.as_str())
        };
        let error_message = if result.error_message.is_empty() {
            None
        } else {
            Some(result.error_message.as_str())
        };
        // exit_code=0 은 정상 종료이므로 항상 전송한다.
        let exit_code = Some(result.exit_code);

        let body = Body {
            command_id: &result.command_id,
            status: status_str,
            output,
            error_message,
            exit_code,
        };

        let resp = self
            .http
            .post(self.url("/internal/telemetry/command-result/"))
            .header("Authorization", self.bearer())
            .json(&body)
            .send()
            .await
            .context("command_result 요청 전송 실패")?;

        if !resp.status().is_success() {
            let status = resp.status();
            let text = resp.text().await.unwrap_or_default();
            anyhow::bail!("command_result 응답 오류 {status}: {text}");
        }

        Ok(())
    }

    // ─── CommandAck ──────────────────────────────────────────────────────────

    /// POST /internal/telemetry/command-ack/
    pub async fn command_ack(&self, command_id: &str) -> Result<()> {
        #[derive(Serialize)]
        struct Body<'a> {
            command_id: &'a str,
        }

        let resp = self
            .http
            .post(self.url("/internal/telemetry/command-ack/"))
            .header("Authorization", self.bearer())
            .json(&Body { command_id })
            .send()
            .await
            .context("command_ack 요청 전송 실패")?;

        if !resp.status().is_success() {
            let status = resp.status();
            let text = resp.text().await.unwrap_or_default();
            anyhow::bail!("command_ack 응답 오류 {status}: {text}");
        }

        Ok(())
    }

    // ─── Pending commands ────────────────────────────────────────────────────

    /// GET /internal/clients/{client_id}/pending-commands/
    ///
    /// 재연결 시 큐에 쌓인 명령을 가져와 클라이언트로 push 한다 (design §4.4).
    pub async fn fetch_pending_commands(
        &self,
        client_id: uuid::Uuid,
    ) -> Result<Vec<PendingCommand>> {
        let url = self.url(&format!(
            "/internal/clients/{}/pending-commands/",
            client_id
        ));

        let resp = self
            .http
            .get(&url)
            .header("Authorization", self.bearer())
            .send()
            .await
            .context("pending-commands 요청 전송 실패")?;

        if !resp.status().is_success() {
            let status = resp.status();
            let text = resp.text().await.unwrap_or_default();
            anyhow::bail!("pending-commands 응답 오류 {status}: {text}");
        }

        let commands: Vec<PendingCommand> = resp
            .json()
            .await
            .context("pending-commands JSON 파싱 실패")?;

        Ok(commands)
    }
}

// ─── PendingCommand (Django GET 응답 구조체) ──────────────────────────────────

/// Django `/internal/clients/<uuid>/pending-commands/` 응답의 단일 항목.
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct PendingCommand {
    pub id: String,
    pub command_type: String,
    /// 가변 파라미터 — Django 측 JSON object
    #[serde(default)]
    pub parameters: serde_json::Value,
    pub priority: u32,
    pub timeout_seconds: u32,
    #[serde(default)]
    pub created_at: Option<String>,
}

// ─── 변환 유틸리티 ────────────────────────────────────────────────────────────

/// proto `CommandResultStatus` 열거형을 Django API 가 기대하는 문자열로 변환한다.
pub fn command_result_status_str(status_i32: i32) -> &'static str {
    match CommandResultStatus::try_from(status_i32) {
        Ok(CommandResultStatus::Completed) => "completed",
        Ok(CommandResultStatus::Error) => "error",
        Ok(CommandResultStatus::Timeout) => "timeout",
        _ => "error", // Unspecified → error 로 보수적 처리
    }
}

/// command_type 문자열 → proto [`CommandType`] 열거형 변환.
///
/// 알 수 없는 값은 `CommandType::Unspecified(0)` 을 반환한다.
pub fn command_type_from_str(s: &str) -> crate::proto::CommandType {
    use crate::proto::CommandType;
    match s {
        "shutdown" => CommandType::Shutdown,
        "restart" => CommandType::Restart,
        "message" => CommandType::Message,
        "kill_process" => CommandType::KillProcess,
        "execute" => CommandType::Execute,
        "install" => CommandType::Install,
        "uninstall" => CommandType::Uninstall,
        "create_user" => CommandType::CreateUser,
        "delete_user" => CommandType::DeleteUser,
        "change_password" => CommandType::ChangePassword,
        "download" => CommandType::Download,
        _ => CommandType::Unspecified,
    }
}

/// `serde_json::Value` → `prost_types::Value` 재귀 변환.
pub fn json_to_prost_value(v: serde_json::Value) -> prost_types::Value {
    use prost_types::value::Kind;
    use prost_types::Value;

    let kind = match v {
        serde_json::Value::Null => Kind::NullValue(0),
        serde_json::Value::Bool(b) => Kind::BoolValue(b),
        serde_json::Value::Number(n) => {
            Kind::NumberValue(n.as_f64().unwrap_or(0.0))
        }
        serde_json::Value::String(s) => Kind::StringValue(s),
        serde_json::Value::Array(arr) => {
            Kind::ListValue(prost_types::ListValue {
                values: arr.into_iter().map(json_to_prost_value).collect(),
            })
        }
        serde_json::Value::Object(map) => {
            Kind::StructValue(prost_types::Struct {
                fields: map
                    .into_iter()
                    .map(|(k, v)| (k, json_to_prost_value(v)))
                    .collect(),
            })
        }
    };

    Value { kind: Some(kind) }
}

/// `serde_json::Value::Object` → `prost_types::Struct` 변환.
///
/// Object 가 아닌 값이면 빈 Struct 를 반환한다.
pub fn json_object_to_prost_struct(v: serde_json::Value) -> prost_types::Struct {
    match v {
        serde_json::Value::Object(map) => prost_types::Struct {
            fields: map
                .into_iter()
                .map(|(k, v)| (k, json_to_prost_value(v)))
                .collect(),
        },
        _ => prost_types::Struct::default(),
    }
}

/// [`PendingCommand`] → proto [`crate::proto::Command`] 변환.
pub fn pending_command_to_proto(cmd: PendingCommand) -> crate::proto::Command {
    use crate::proto::{Command, DeliveryMode};

    let cmd_type = command_type_from_str(&cmd.command_type);
    let parameters = if cmd.parameters.is_null() || cmd.parameters == serde_json::Value::Null {
        None
    } else {
        Some(json_object_to_prost_struct(cmd.parameters))
    };

    // created_at: ISO 8601 문자열 → prost_types::Timestamp 파싱 (실패 시 None)
    let created_at = cmd.created_at.as_deref().and_then(parse_iso8601_timestamp);

    Command {
        id: cmd.id,
        r#type: cmd_type as i32,
        parameters,
        timeout_sec: cmd.timeout_seconds,
        priority: cmd.priority,
        created_at,
        delivery_mode: DeliveryMode::Queue as i32,
    }
}

/// ISO 8601 문자열을 `prost_types::Timestamp` 로 변환한다.
///
/// 파싱 실패 시 `None` 반환.
fn parse_iso8601_timestamp(s: &str) -> Option<prost_types::Timestamp> {
    // 간단한 수동 파싱: "2024-01-15T10:30:00Z" 또는 "2024-01-15T10:30:00.000000Z" 형식
    // 완전한 구현은 chrono 를 사용하겠지만 의존성 추가를 피하기 위해 기본적인 파싱만 수행.
    let s = s.trim_end_matches('Z').trim_end_matches('+').trim();
    let parts: Vec<&str> = s.splitn(2, 'T').collect();
    if parts.len() != 2 {
        return None;
    }
    let date_parts: Vec<&str> = parts[0].split('-').collect();
    let time_str = parts[1].split('+').next()?.split('Z').next()?;
    let time_parts: Vec<&str> = time_str.splitn(2, '.').collect();
    let hms: Vec<&str> = time_parts[0].split(':').collect();

    if date_parts.len() != 3 || hms.len() != 3 {
        return None;
    }

    let year: i64 = date_parts[0].parse().ok()?;
    let month: i64 = date_parts[1].parse().ok()?;
    let day: i64 = date_parts[2].parse().ok()?;
    let hour: i64 = hms[0].parse().ok()?;
    let min: i64 = hms[1].parse().ok()?;
    let sec: i64 = hms[2].parse().ok()?;

    // 단순 근사: 정확한 윤초/윤년 처리 없이 에포크 계산
    let days_from_epoch = days_since_epoch(year, month, day)?;
    let seconds =
        days_from_epoch * 86400 + hour * 3600 + min * 60 + sec;

    Some(prost_types::Timestamp {
        seconds,
        nanos: 0,
    })
}

fn days_since_epoch(year: i64, month: i64, day: i64) -> Option<i64> {
    if year < 1970 || month < 1 || month > 12 || day < 1 || day > 31 {
        return None;
    }
    // Tomohiko Sakamoto 알고리즘 기반 간략 계산
    let y = if month <= 2 { year - 1 } else { year };
    let m = month as i64;
    let d = day;
    let era = y / 400;
    let yoe = y - era * 400;
    let doy = (153 * (m + (if month > 2 { -3 } else { 9 })) + 2) / 5 + d - 1;
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    let days_since_0 = era * 146097 + doe - 719468;
    Some(days_since_0)
}

/// proto [`Heartbeat`] 를 Django heartbeat API 가 기대하는 JSON body 로 변환.
fn heartbeat_to_json(
    client_id: uuid::Uuid,
    hb: &Heartbeat,
) -> serde_json::Value {
    let mut map = serde_json::Map::new();
    map.insert(
        "client_id".to_owned(),
        serde_json::Value::String(client_id.to_string()),
    );
    map.insert("full".to_owned(), serde_json::Value::Bool(hb.full));
    map.insert(
        "cpu_usage".to_owned(),
        serde_json::Value::Number(
            serde_json::Number::from_f64(hb.cpu_usage).unwrap_or(serde_json::Number::from(0)),
        ),
    );
    map.insert(
        "ram_usage_percent".to_owned(),
        serde_json::Value::Number(
            serde_json::Number::from_f64(hb.ram_usage_percent)
                .unwrap_or(serde_json::Number::from(0)),
        ),
    );

    if hb.full {
        if hb.ram_used_gb != 0.0 {
            map.insert(
                "ram_used".to_owned(),
                serde_json::Value::Number(
                    serde_json::Number::from_f64(hb.ram_used_gb)
                        .unwrap_or(serde_json::Number::from(0)),
                ),
            );
        }
        if let Some(disk) = &hb.disk_usage {
            // prost_types::Struct → serde_json::Value
            map.insert(
                "disk_usage".to_owned(),
                prost_struct_to_json(disk.clone()),
            );
        }
        if !hb.current_user.is_empty() {
            map.insert(
                "current_user".to_owned(),
                serde_json::Value::String(hb.current_user.clone()),
            );
        }
        if hb.uptime_sec != 0 {
            map.insert(
                "uptime".to_owned(),
                serde_json::Value::Number(serde_json::Number::from(hb.uptime_sec)),
            );
        }
        if !hb.processes.is_empty() {
            map.insert(
                "processes".to_owned(),
                serde_json::Value::Array(
                    hb.processes
                        .iter()
                        .map(|p| serde_json::Value::String(p.clone()))
                        .collect(),
                ),
            );
        }
        if !hb.ip_address.is_empty() {
            map.insert(
                "ip_address".to_owned(),
                serde_json::Value::String(hb.ip_address.clone()),
            );
        }
    }

    serde_json::Value::Object(map)
}

/// `prost_types::Struct` → `serde_json::Value` 재귀 변환.
fn prost_struct_to_json(s: prost_types::Struct) -> serde_json::Value {
    let map: serde_json::Map<String, serde_json::Value> = s
        .fields
        .into_iter()
        .map(|(k, v)| (k, prost_value_to_json(v)))
        .collect();
    serde_json::Value::Object(map)
}

fn prost_value_to_json(v: prost_types::Value) -> serde_json::Value {
    use prost_types::value::Kind;
    match v.kind {
        None | Some(Kind::NullValue(_)) => serde_json::Value::Null,
        Some(Kind::BoolValue(b)) => serde_json::Value::Bool(b),
        Some(Kind::NumberValue(n)) => serde_json::Value::Number(
            serde_json::Number::from_f64(n).unwrap_or(serde_json::Number::from(0)),
        ),
        Some(Kind::StringValue(s)) => serde_json::Value::String(s),
        Some(Kind::ListValue(l)) => {
            serde_json::Value::Array(l.values.into_iter().map(prost_value_to_json).collect())
        }
        Some(Kind::StructValue(s)) => prost_struct_to_json(s),
    }
}

// ─── 단위 테스트 ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use mockito::Server;
    use serde_json::json;

    /// DjangoClient 를 mock 서버 URL 로 생성하는 헬퍼.
    fn make_client(server: &mockito::ServerGuard) -> DjangoClient {
        DjangoClient::new(server.url(), "test-token")
    }

    // ── presence ─────────────────────────────────────────────────────────

    #[tokio::test]
    async fn presence_connect_sends_correct_request() {
        let mut server = Server::new_async().await;
        let client_id = uuid::Uuid::new_v4();

        let mock = server
            .mock("POST", "/internal/presence/")
            .match_header("Authorization", "Bearer test-token")
            .match_body(mockito::Matcher::Json(json!({
                "client_id": client_id.to_string(),
                "event": "connect"
            })))
            .with_status(200)
            .with_body("{}")
            .create_async()
            .await;

        let client = make_client(&server);
        client.presence(client_id, true).await.unwrap();
        mock.assert_async().await;
    }

    #[tokio::test]
    async fn presence_disconnect_sends_correct_request() {
        let mut server = Server::new_async().await;
        let client_id = uuid::Uuid::new_v4();

        let mock = server
            .mock("POST", "/internal/presence/")
            .match_header("Authorization", "Bearer test-token")
            .match_body(mockito::Matcher::Json(json!({
                "client_id": client_id.to_string(),
                "event": "disconnect"
            })))
            .with_status(200)
            .with_body("{}")
            .create_async()
            .await;

        let client = make_client(&server);
        client.presence(client_id, false).await.unwrap();
        mock.assert_async().await;
    }

    // ── heartbeat ────────────────────────────────────────────────────────

    #[tokio::test]
    async fn heartbeat_sends_correct_request() {
        let mut server = Server::new_async().await;
        let client_id = uuid::Uuid::new_v4();

        let hb = Heartbeat {
            full: false,
            cpu_usage: 42.5,
            ram_usage_percent: 55.0,
            ..Default::default()
        };

        let mock = server
            .mock("POST", "/internal/telemetry/heartbeat/")
            .match_header("Authorization", "Bearer test-token")
            .match_body(mockito::Matcher::PartialJson(json!({
                "client_id": client_id.to_string(),
                "full": false,
                "cpu_usage": 42.5,
                "ram_usage_percent": 55.0
            })))
            .with_status(200)
            .with_body("{}")
            .create_async()
            .await;

        let client = make_client(&server);
        client.heartbeat(client_id, &hb).await.unwrap();
        mock.assert_async().await;
    }

    // ── command_result ───────────────────────────────────────────────────

    #[tokio::test]
    async fn command_result_sends_correct_request() {
        let mut server = Server::new_async().await;

        let result = CommandResult {
            command_id: "cmd-001".to_owned(),
            status: CommandResultStatus::Completed as i32,
            output: "done".to_owned(),
            error_message: String::new(),
            exit_code: 0,
        };

        let mock = server
            .mock("POST", "/internal/telemetry/command-result/")
            .match_header("Authorization", "Bearer test-token")
            .match_body(mockito::Matcher::PartialJson(json!({
                "command_id": "cmd-001",
                "status": "completed",
                "output": "done",
                "exit_code": 0
            })))
            .with_status(200)
            .with_body("{}")
            .create_async()
            .await;

        let client = make_client(&server);
        client.command_result(&result).await.unwrap();
        mock.assert_async().await;
    }

    // ── fetch_pending_commands ───────────────────────────────────────────

    #[tokio::test]
    async fn fetch_pending_commands_parses_json_array() {
        let mut server = Server::new_async().await;
        let client_id = uuid::Uuid::new_v4();

        let body = json!([
            {
                "id": "aaaa-bbbb",
                "command_type": "shutdown",
                "parameters": {"delay_sec": 30},
                "priority": 1,
                "timeout_seconds": 60,
                "created_at": "2024-01-15T10:30:00Z"
            }
        ]);

        let mock = server
            .mock(
                "GET",
                format!("/internal/clients/{}/pending-commands/", client_id).as_str(),
            )
            .match_header("Authorization", "Bearer test-token")
            .with_status(200)
            .with_header("content-type", "application/json")
            .with_body(body.to_string())
            .create_async()
            .await;

        let client = make_client(&server);
        let cmds = client.fetch_pending_commands(client_id).await.unwrap();

        assert_eq!(cmds.len(), 1);
        assert_eq!(cmds[0].id, "aaaa-bbbb");
        assert_eq!(cmds[0].command_type, "shutdown");
        assert_eq!(cmds[0].priority, 1);
        assert_eq!(cmds[0].timeout_seconds, 60);
        mock.assert_async().await;
    }

    // ── conversion helpers ───────────────────────────────────────────────

    #[test]
    fn command_type_from_str_known_values() {
        use crate::proto::CommandType;
        assert_eq!(command_type_from_str("shutdown"), CommandType::Shutdown);
        assert_eq!(command_type_from_str("restart"), CommandType::Restart);
        assert_eq!(command_type_from_str("execute"), CommandType::Execute);
        assert_eq!(command_type_from_str("unknown_xyz"), CommandType::Unspecified);
    }

    #[test]
    fn json_to_prost_value_roundtrip() {
        let json_val = json!({"key": "value", "num": 42.0, "flag": true});
        let prost_val = json_to_prost_value(json_val);
        match prost_val.kind {
            Some(prost_types::value::Kind::StructValue(s)) => {
                assert!(s.fields.contains_key("key"));
                assert!(s.fields.contains_key("num"));
                assert!(s.fields.contains_key("flag"));
            }
            other => panic!("expected StructValue, got {other:?}"),
        }
    }

    #[test]
    fn command_result_status_str_maps_correctly() {
        assert_eq!(
            command_result_status_str(CommandResultStatus::Completed as i32),
            "completed"
        );
        assert_eq!(
            command_result_status_str(CommandResultStatus::Error as i32),
            "error"
        );
        assert_eq!(
            command_result_status_str(CommandResultStatus::Timeout as i32),
            "timeout"
        );
    }
}
