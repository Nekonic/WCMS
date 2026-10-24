from rest_framework import serializers

from audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ["id", "actor", "action", "target", "detail", "created_at"]

    def get_actor(self, obj: AuditLog) -> str | None:
        return obj.actor.get_username() if obj.actor else None
