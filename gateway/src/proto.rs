/// Generated protobuf types for `wcms.v1`.
///
/// The `include!` macro splices in the file emitted by `prost-build` during
/// `cargo build`.  All message types live in the `wcms::v1` sub-module so
/// callers can write `proto::wcms::v1::ServerEnvelope`, etc.
pub mod wcms {
    pub mod v1 {
        include!(concat!(env!("OUT_DIR"), "/wcms.v1.rs"));
    }
}

// Convenience re-exports used throughout the crate.
pub use wcms::v1::{
    client_envelope, server_envelope, ClientEnvelope, Command, CommandAck, CommandResult,
    CommandResultStatus, CommandType, DeliveryMode, Heartbeat, Hello, LogEvent, LogLevel,
    ServerEnvelope, Welcome,
};
