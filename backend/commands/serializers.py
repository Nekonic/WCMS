from rest_framework import serializers

from .models import Command


class CommandSerializer(serializers.ModelSerializer):
    issuer = serializers.SerializerMethodField()

    class Meta:
        model = Command
        fields = ["id", "client", "command_type", "parameters", "priority",
                  "delivery_mode", "status", "result", "error_message",
                  "timeout_seconds", "issuer", "expires_at", "created_at",
                  "sent_at", "started_at", "completed_at"]

    def get_issuer(self, obj):
        return obj.issuer.username if obj.issuer_id else None


class CommandCreateSerializer(serializers.Serializer):
    command_type = serializers.CharField(max_length=64)
    parameters = serializers.JSONField(required=False, default=dict)
    priority = serializers.IntegerField(required=False, default=5, min_value=1, max_value=10)
    timeout_seconds = serializers.IntegerField(required=False, default=300, min_value=1)
    delivery_mode = serializers.ChoiceField(
        choices=Command.DeliveryMode.choices, required=False,
    )
