from audit.models import AuditLog


def record(actor, action: str, target: str = "", **detail) -> AuditLog:
    user = actor if actor is not None and actor.is_authenticated else None
    return AuditLog.objects.create(actor=user, action=action, target=target, detail=detail)
