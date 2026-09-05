from core.models import AuditLog


def log(action, user, record_id, details):
    return AuditLog.objects.create(
        action_type=action,
        user=user,
        record_id=record_id,
        details=details,
    )
