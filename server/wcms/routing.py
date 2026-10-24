from channels.security.websocket import AllowedHostsOriginValidator
from django.urls import path

from agent.consumers import AgentConsumer
from live.consumers import LiveConsumer

websocket_urlpatterns = [
    path("client/ws", AgentConsumer.as_asgi()),
    path("ws/live", AllowedHostsOriginValidator(LiveConsumer.as_asgi())),
]
