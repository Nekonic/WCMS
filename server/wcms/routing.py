from django.urls import path

from agent.consumers import AgentConsumer

websocket_urlpatterns = [
    path("client/ws", AgentConsumer.as_asgi()),
]
