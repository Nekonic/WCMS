from django.urls import path

from .views import BulkCommandView, ClientCommandsView, CommandListView

urlpatterns = [
    path("pcs/<uuid:pc_id>/commands/", ClientCommandsView.as_view(), name="client-commands"),
    path("commands/bulk/", BulkCommandView.as_view(), name="command-bulk"),
    path("commands/", CommandListView.as_view(), name="command-list"),
]
