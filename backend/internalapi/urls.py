"""internalapi URL 패턴 (prefix: /internal/)."""
from django.urls import path

from .views import (
    CommandAckView,
    CommandResultView,
    HeartbeatView,
    PendingCommandsView,
    PresenceView,
)

urlpatterns = [
    path("presence/", PresenceView.as_view(), name="internal-presence"),
    path("telemetry/heartbeat/", HeartbeatView.as_view(), name="internal-heartbeat"),
    path("telemetry/command-result/", CommandResultView.as_view(), name="internal-command-result"),
    path("telemetry/command-ack/", CommandAckView.as_view(), name="internal-command-ack"),
    path(
        "clients/<uuid:client_id>/pending-commands/",
        PendingCommandsView.as_view(),
        name="internal-pending-commands",
    ),
]
