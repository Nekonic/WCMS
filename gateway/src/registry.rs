//! In-memory connection registry — the authoritative presence source of truth.
//!
//! # Design (docs/REWRITE_DESIGN.md §3, §4.1)
//!
//! Every live WebSocket connection owns an mpsc channel whose `Sender` is
//! stored here, keyed by `client_id` (UUID).  Because we store one entry per
//! *currently connected* client:
//!
//! - `is_online(id)` = entry exists → O(1), no timeout polling.
//! - A new connection for the same client (reconnect) calls `register` again,
//!   which atomically replaces the old sender.  The old write-task draining the
//!   defunct sender will notice the channel closed and exit.
//! - On socket close/error the connection handler calls `unregister(id,
//!   &sender)`.  We compare the stored sender with the caller's copy so that a
//!   *stale* disconnect from a superseded connection cannot evict the newer one.
//!
//! `DashMap` gives lock-free concurrent access from the many per-connection
//! tasks without blocking the async runtime.

use dashmap::DashMap;
use std::sync::Arc;
use tokio::sync::mpsc;
use uuid::Uuid;

use crate::proto::ServerEnvelope;

/// Channel capacity for the per-connection outbound queue.
const OUTBOUND_CAPACITY: usize = 64;

/// A cloneable handle to the shared registry.
#[derive(Clone, Default)]
pub struct Registry {
    inner: Arc<DashMap<Uuid, mpsc::Sender<ServerEnvelope>>>,
}

impl Registry {
    pub fn new() -> Self {
        Self {
            inner: Arc::new(DashMap::new()),
        }
    }

    /// Create a fresh outbound channel and register it for `client_id`.
    ///
    /// If there is already a sender stored for that id it is replaced; the
    /// old connection's write-task will detect the channel closed and exit,
    /// which triggers its `unregister` call — but that call is a no-op because
    /// the stored sender will already differ.
    pub fn register(&self, client_id: Uuid) -> mpsc::Receiver<ServerEnvelope> {
        let (tx, rx) = mpsc::channel(OUTBOUND_CAPACITY);
        self.inner.insert(client_id, tx);
        rx
    }

    /// Remove the entry for `client_id` **only if** `sender` is still the
    /// current sender (pointer equality via `Sender::same_channel`).
    ///
    /// This prevents a stale disconnect from a superseded connection from
    /// evicting the entry created by the newer connection.
    pub fn unregister(&self, client_id: Uuid, sender: &mpsc::Sender<ServerEnvelope>) {
        // Use a remove-if pattern: peek with a read lock, remove only when matched.
        let should_remove = self
            .inner
            .get(&client_id)
            .map(|stored| stored.same_channel(sender))
            .unwrap_or(false);

        if should_remove {
            self.inner.remove(&client_id);
        }
    }

    /// Look up the current sender for `client_id` (if online) and clone it.
    ///
    /// Returns `None` if the client is not connected.
    pub fn sender(&self, client_id: Uuid) -> Option<mpsc::Sender<ServerEnvelope>> {
        self.inner.get(&client_id).map(|s| s.clone())
    }

    /// Push a `ServerEnvelope` to the connection for `client_id`.
    ///
    /// Returns `true` if the client is online and the message was queued,
    /// `false` if the client is unknown or the channel is closed/full.
    pub fn push(&self, client_id: Uuid, msg: ServerEnvelope) -> bool {
        if let Some(sender) = self.inner.get(&client_id) {
            sender.try_send(msg).is_ok()
        } else {
            false
        }
    }

    /// Returns `true` if a live connection is registered for `client_id`.
    pub fn is_online(&self, client_id: Uuid) -> bool {
        self.inner.contains_key(&client_id)
    }

    /// Number of currently connected clients.
    pub fn online_count(&self) -> usize {
        self.inner.len()
    }

    /// IDs of all currently connected clients.
    pub fn online_ids(&self) -> Vec<Uuid> {
        self.inner.iter().map(|entry| *entry.key()).collect()
    }
}

// ─── Tests ───────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::proto::{server_envelope, Welcome};
    use prost_types::Timestamp;

    fn make_welcome() -> ServerEnvelope {
        ServerEnvelope {
            payload: Some(server_envelope::Payload::Welcome(Welcome {
                server_time: Some(Timestamp {
                    seconds: 1_000_000,
                    nanos: 0,
                }),
                ping_interval_sec: 15,
            })),
        }
    }

    #[test]
    fn register_makes_client_online() {
        let registry = Registry::new();
        let id = Uuid::new_v4();
        let _rx = registry.register(id);
        assert!(registry.is_online(id));
        assert_eq!(registry.online_count(), 1);
    }

    #[test]
    fn unregister_removes_client() {
        let registry = Registry::new();
        let id = Uuid::new_v4();
        let _rx = registry.register(id);

        // Grab the sender so we can pass it to unregister.
        let sender = registry.sender(id).unwrap();
        registry.unregister(id, &sender);

        assert!(!registry.is_online(id));
        assert_eq!(registry.online_count(), 0);
    }

    #[test]
    fn reconnect_supersedes_old_sender() {
        let registry = Registry::new();
        let id = Uuid::new_v4();

        // First connection.
        let _rx1 = registry.register(id);
        let old_sender = registry.sender(id).unwrap();

        // Second connection (reconnect) — replaces the entry.
        let _rx2 = registry.register(id);
        let new_sender = registry.sender(id).unwrap();

        // The new sender must differ from the old one.
        assert!(!old_sender.same_channel(&new_sender));
        assert!(registry.is_online(id));
        assert_eq!(registry.online_count(), 1);
    }

    #[test]
    fn stale_unregister_does_not_evict_new_connection() {
        let registry = Registry::new();
        let id = Uuid::new_v4();

        // First connection.
        let _rx1 = registry.register(id);
        let old_sender = registry.sender(id).unwrap();

        // Second connection (reconnect).
        let _rx2 = registry.register(id);

        // Stale disconnect from the first connection — must NOT evict.
        registry.unregister(id, &old_sender);

        assert!(registry.is_online(id), "new connection must still be online");
        assert_eq!(registry.online_count(), 1);
    }

    #[tokio::test]
    async fn push_returns_false_for_unknown_id() {
        let registry = Registry::new();
        let unknown = Uuid::new_v4();
        assert!(!registry.push(unknown, make_welcome()));
    }

    #[tokio::test]
    async fn push_delivers_to_known_client() {
        let registry = Registry::new();
        let id = Uuid::new_v4();
        let mut rx = registry.register(id);

        let msg = make_welcome();
        assert!(registry.push(id, msg));

        // The receiver should have the message immediately.
        let received = rx.try_recv().expect("message should be in channel");
        assert!(received.payload.is_some());
    }

    #[test]
    fn online_ids_returns_all_connected() {
        let registry = Registry::new();
        let id1 = Uuid::new_v4();
        let id2 = Uuid::new_v4();
        let _rx1 = registry.register(id1);
        let _rx2 = registry.register(id2);

        let mut ids = registry.online_ids();
        ids.sort();
        let mut expected = vec![id1, id2];
        expected.sort();
        assert_eq!(ids, expected);
    }
}
