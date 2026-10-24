from django.urls import path

from clientapi.consumers import ClientConsumer

websocket_urlpatterns = [
    path("client/ws", ClientConsumer.as_asgi()),
]
