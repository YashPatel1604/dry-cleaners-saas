from typing import Optional
import hashlib
import hmac
import secrets

from rest_framework.exceptions import ValidationError

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


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify(token: str, token_hash: str) -> bool:
    return hmac.compare_digest(hash_token(token), token_hash)


def generate_invite_token() -> str:
    return generate_token()


def hash_invite_token(token: str) -> str:
    return hash_token(token)


def verify_invite_token(token: str, token_hash: str) -> bool:
    return verify(token, token_hash)


def parse_limit_offset(request, *, default_limit: Optional[int] = None, max_limit: int = 200):
    limit_raw = request.query_params.get("limit")
    offset_raw = request.query_params.get("offset")

    if limit_raw is None and offset_raw is None and default_limit is None:
        return None, None

    try:
        if limit_raw is None:
            limit = default_limit if default_limit is not None else max_limit
        else:
            limit = int(limit_raw)
        offset = 0 if offset_raw is None else int(offset_raw)
    except ValueError as exc:
        raise ValidationError({"pagination": "limit and offset must be integers."}) from exc

    if limit < 1 or offset < 0:
        raise ValidationError({"pagination": "limit must be >= 1 and offset >= 0."})

    return min(limit, max_limit), offset
