from django.conf import settings
from django.core.mail import send_mail


def _build_accept_url(token: str) -> str | None:
    base_url = getattr(settings, "FRONTEND_BASE_URL", "").strip()
    if not base_url:
        return None
    return f"{base_url.rstrip('/')}/invites/accept/?token={token}"


def send_tenant_invite_email(*, tenant, email: str, token: str, invited_by_user):
    accept_url = _build_accept_url(token)
    inviter = getattr(invited_by_user, "username", None) or ""

    lines = [
        f"You have been invited to join {tenant.name}.",
    ]
    if inviter:
        lines.append(f"Invited by: {inviter}")

    if accept_url:
        lines.append(f"Accept invite: {accept_url}")
        lines.append(f"Token: {token}")
    else:
        lines.append("Use this token to accept the invite:")
        lines.append(token)

    message = "\n".join(lines)

    send_mail(
        subject=f"You're invited to {tenant.name}",
        message=message,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[email],
        fail_silently=False,
    )
