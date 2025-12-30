from typing import Any, Dict, Optional

from .models import AuditEvent


def actor_from_request(request) -> Dict[str, str]:
    """
    Returns a small dict used to populate actor fields.
    """
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        label = getattr(user, "email", "") or getattr(user, "username", "") or str(user.pk)
        return {
            "actor_type": AuditEvent.ActorType.USER,
            "actor_id": str(user.pk),
            "actor_label": label[:255],
        }

    return {
        "actor_type": AuditEvent.ActorType.SYSTEM,
        "actor_id": "",
        "actor_label": "",
    }


def emit_event(
    *,
    tenant,
    request_id: str,
    actor: Dict[str, str],
    action: str,
    entity_type: str,
    entity_id: Any,
    before: Optional[dict] = None,
    after: Optional[dict] = None,
    metadata: Optional[dict] = None,
) -> AuditEvent:
    """
    Writes an AuditEvent row.
    Keep this tiny + boring. Business logic stays elsewhere.
    """
    return AuditEvent.objects.create(
        tenant=tenant,
        request_id=request_id or "",
        actor_type=actor.get("actor_type", AuditEvent.ActorType.SYSTEM),
        actor_id=actor.get("actor_id", ""),
        actor_label=actor.get("actor_label", ""),
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        before=before,
        after=after,
        metadata=metadata,
    )
