from typing import Optional
import hashlib
import hmac
import secrets

from .models import TenantMembershipEvent, TenantMembership


def record_membership_event(
    *,
    tenant,
    actor,
    subject_user,
    action: str,
    old_role: Optional[str] = None,
    new_role: Optional[str] = None,
    is_active_before: Optional[bool] = None,
    is_active_after: Optional[bool] = None,
    metadata: Optional[dict] = None,
) -> TenantMembershipEvent:
    return TenantMembershipEvent.objects.create(
        tenant=tenant,
        actor=actor,
        subject_user=subject_user,
        action=action,
        old_role=old_role,
        new_role=new_role,
        is_active_before=is_active_before,
        is_active_after=is_active_after,
        metadata=metadata or {},
    )


def active_owner_admin_count(*, tenant) -> int:
    return TenantMembership.objects.filter(
        tenant=tenant,
        role=TenantMembership.Role.OWNER_ADMIN,
        is_active=True,
    ).count()


def generate_invite_token() -> str:
    return secrets.token_urlsafe(32)


def hash_invite_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_invite_token(token: str, token_hash: str) -> bool:
    return hmac.compare_digest(hash_invite_token(token), token_hash)
