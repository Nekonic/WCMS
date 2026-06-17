//! WCMS realtime gateway — library root.
//!
//! Exposes internal modules so that integration tests (in `tests/`) and the
//! `main.rs` binary can share code without duplication.

pub mod django;
pub mod proto;
pub mod push;
pub mod registry;
pub mod ws;

// ─── Proto codec tests ───────────────────────────────────────────────────────

#[cfg(test)]
mod proto_codec_tests {
    use prost::Message;
    use prost_types::{Struct, Timestamp, Value, value::Kind};

    use crate::proto::{
        client_envelope, server_envelope, ClientEnvelope, Command, CommandType,
        DeliveryMode, Hello, ServerEnvelope, Welcome,
    };

    /// Build a `Struct` with a single string field, suitable for use as
    /// `Command::parameters` without depending on complex protobuf map syntax.
    fn simple_struct(key: &str, val: &str) -> Struct {
        let mut fields = std::collections::BTreeMap::new();
        fields.insert(
            key.to_owned(),
            Value {
                kind: Some(Kind::StringValue(val.to_owned())),
            },
        );
        Struct { fields }
    }

    #[test]
    fn server_envelope_command_roundtrip() {
        let original = ServerEnvelope {
            payload: Some(server_envelope::Payload::Command(Command {
                id: "d4e5f6a7-0000-0000-0000-000000000000".to_owned(),
                r#type: CommandType::Shutdown as i32,
                parameters: Some(simple_struct("delay_sec", "30")),
                timeout_sec: 60,
                priority: 1,
                created_at: Some(Timestamp {
                    seconds: 1_700_000_000,
                    nanos: 0,
                }),
                delivery_mode: DeliveryMode::DropIfOffline as i32,
            })),
        };

        // Encode.
        let mut buf = Vec::new();
        original.encode(&mut buf).unwrap();

        // Decode.
        let decoded = ServerEnvelope::decode(buf.as_slice()).unwrap();

        // Assert.
        match decoded.payload {
            Some(server_envelope::Payload::Command(cmd)) => {
                assert_eq!(cmd.id, "d4e5f6a7-0000-0000-0000-000000000000");
                assert_eq!(cmd.r#type, CommandType::Shutdown as i32);
                assert_eq!(cmd.timeout_sec, 60);
                assert_eq!(cmd.priority, 1);
                assert_eq!(
                    cmd.delivery_mode,
                    DeliveryMode::DropIfOffline as i32
                );
                let params = cmd.parameters.unwrap();
                assert_eq!(
                    params.fields["delay_sec"].kind,
                    Some(prost_types::value::Kind::StringValue("30".to_owned()))
                );
            }
            other => panic!("unexpected payload: {other:?}"),
        }
    }

    #[test]
    fn server_envelope_welcome_roundtrip() {
        let original = ServerEnvelope {
            payload: Some(server_envelope::Payload::Welcome(Welcome {
                server_time: Some(Timestamp {
                    seconds: 1_750_000_000,
                    nanos: 42,
                }),
                ping_interval_sec: 15,
            })),
        };

        let mut buf = Vec::new();
        original.encode(&mut buf).unwrap();
        let decoded = ServerEnvelope::decode(buf.as_slice()).unwrap();

        match decoded.payload {
            Some(server_envelope::Payload::Welcome(w)) => {
                assert_eq!(w.ping_interval_sec, 15);
                let ts = w.server_time.unwrap();
                assert_eq!(ts.seconds, 1_750_000_000);
                assert_eq!(ts.nanos, 42);
            }
            other => panic!("unexpected payload: {other:?}"),
        }
    }

    #[test]
    fn client_envelope_hello_roundtrip() {
        let client_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890";
        let original = ClientEnvelope {
            payload: Some(client_envelope::Payload::Hello(Hello {
                client_id: client_id.to_owned(),
                client_version: "0.1.0".to_owned(),
            })),
        };

        let mut buf = Vec::new();
        original.encode(&mut buf).unwrap();
        let decoded = ClientEnvelope::decode(buf.as_slice()).unwrap();

        match decoded.payload {
            Some(client_envelope::Payload::Hello(h)) => {
                assert_eq!(h.client_id, client_id);
                assert_eq!(h.client_version, "0.1.0");
            }
            other => panic!("unexpected payload: {other:?}"),
        }
    }
}
