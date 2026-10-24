from channels.security.websocket import AllowedHostsOriginValidator
from django.urls import path

from clientapi.consumers import ClientConsumer
from web.consumers import LiveConsumer

websocket_urlpatterns = [
    path("client/ws", ClientConsumer.as_asgi()),
    path("ws/live", AllowedHostsOriginValidator(LiveConsumer.as_asgi())),
]
