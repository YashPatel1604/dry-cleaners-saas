from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound
from django.db import transaction
from django.utils import timezone
import re
from django.contrib.auth import get_user_model
from .models import (
    Tenant,
    TenantConfigEvent,
    TenantMembership,
    TenantMembershipEvent,
    TenantInvite,
    TenantInviteEvent,
)
from .serializers import (
    TenantSerializer,
    TenantCreateSerializer,
    TenantDefaultsSerializer,
    TenantMembershipSerializer,
    TenantMembershipCreateSerializer,
    TenantMembershipUpdateSerializer,
    TenantInviteCreateSerializer,
    TenantInviteSerializer,
    InviteAcceptSerializer,
)
from .permissions import IsTenantMember, IsTenantAdmin, get_active_membership
from .utils import (
    record_membership_event,
    active_owner_admin_count,
    generate_invite_token,
    hash_invite_token,
)
from datetime import timedelta
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes


class TenantCreateView(generics.CreateAPIView):
    queryset = Tenant.objects.all()
    serializer_class = TenantCreateSerializer
    permission_classes = [permissions.IsAuthenticated]


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="X-Tenant",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.HEADER,
            required=True,
            description="Tenant slug (e.g. store-1)"
        )
    ]
)
class TenantMeView(generics.RetrieveAPIView):
    serializer_class = TenantSerializer
    permission_classes = [IsTenantMember]

    def get_object(self):
        return self.request.tenant


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="X-Tenant",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.HEADER,
            required=True,
            description="Tenant slug (e.g. store-1)"
        )
    ]
)
class TenantDefaultsView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/tenants/defaults/
    PATCH /api/tenants/defaults/
    Updates the tenant's default pickup promise settings.
    """
    serializer_class = TenantDefaultsSerializer
    permission_classes = [IsTenantMember]

    def get_object(self):
        return self.request.tenant


class TenantSettingsView(APIView):
    permission_classes = [IsTenantAdmin]

    def patch(self, request):
        tenant = request.tenant
        updates = {}
        events = []

        if "collects_tax" in request.data:
            raw_collects_tax = request.data.get("collects_tax")
            if isinstance(raw_collects_tax, bool):
                collects_tax = raw_collects_tax
            elif isinstance(raw_collects_tax, str):
                normalized = raw_collects_tax.strip().lower()
                if normalized in ("true", "1", "yes", "y"):
                    collects_tax = True
                elif normalized in ("false", "0", "no", "n"):
                    collects_tax = False
                else:
                    raise ValidationError(
                        {"collects_tax": "Must be a boolean."}
                    )
            else:
                collects_tax = bool(raw_collects_tax)
            if tenant.collects_tax != collects_tax:
                events.append(
                    TenantConfigEvent(
                        tenant=tenant,
                        actor=request.user,
                        key="collects_tax",
                        old_value=str(tenant.collects_tax),
                        new_value=str(collects_tax),
                    )
                )
                updates["collects_tax"] = collects_tax

        if "tax_rate_bps" in request.data:
            try:
                tax_rate_bps = int(request.data.get("tax_rate_bps"))
            except Exception as exc:
                raise ValidationError({"tax_rate_bps": "Must be an integer."}) from exc
            if tax_rate_bps < 0 or tax_rate_bps > 2000:
                raise ValidationError(
                    {"tax_rate_bps": "Must be between 0 and 2000."}
                )
            if tenant.tax_rate_bps != tax_rate_bps:
                events.append(
                    TenantConfigEvent(
                        tenant=tenant,
                        actor=request.user,
                        key="tax_rate_bps",
                        old_value=str(tenant.tax_rate_bps),
                        new_value=str(tax_rate_bps),
                    )
                )
                updates["tax_rate_bps"] = tax_rate_bps

        if updates:
            for key, value in updates.items():
                setattr(tenant, key, value)
            tenant.save(update_fields=list(updates.keys()))
            TenantConfigEvent.objects.bulk_create(events)

        return Response(
            {
                "tenant": {"id": tenant.id, "slug": tenant.slug},
                "collects_tax": tenant.collects_tax,
                "tax_rate_bps": tenant.tax_rate_bps,
            }
        )


class MeView(APIView):
    permission_classes = [IsTenantMember]

    def get(self, request):
        membership = get_active_membership(
            user=request.user, tenant=request.tenant, request=request
        )
        memberships = (
            TenantMembership.objects.filter(user=request.user)
            .select_related("tenant")
            .order_by("tenant__slug")
        )
        tenant_list = [
            {
                "slug": m.tenant.slug,
                "role": m.role,
                "is_active": m.is_active,
            }
            for m in memberships
        ]
        return Response(
            {
                "user": {"id": request.user.id, "username": request.user.username},
                "tenant": {"id": request.tenant.id, "slug": request.tenant.slug},
                "membership": {
                    "role": membership.role if membership else None,
                    "is_active": membership.is_active if membership else None,
                },
                "tenants": tenant_list,
            }
        )


class TenantBootstrapView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        slug = (request.data.get("slug") or "").strip()
        name = (request.data.get("name") or "").strip()
        if not slug:
            raise ValidationError({"slug": "Required."})
        if not name:
            raise ValidationError({"name": "Required."})

        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            raise ValidationError(
                {"slug": "Invalid format. Use lowercase letters, numbers, and hyphens."}
            )

        if Tenant.objects.filter(slug=slug).exists():
            return Response(
                {"slug": "Tenant slug already exists."},
                status=status.HTTP_409_CONFLICT,
            )

        tenant_fields = {"slug": slug, "name": name}
        config_events = []

        if "tax_enabled" in request.data:
            collects_tax = bool(request.data.get("tax_enabled"))
            tenant_fields["collects_tax"] = collects_tax
        if "tax_rate_bps" in request.data:
            try:
                tax_rate_bps = int(request.data.get("tax_rate_bps"))
            except Exception as exc:
                raise ValidationError({"tax_rate_bps": "Must be an integer."}) from exc
            if tax_rate_bps < 0 or tax_rate_bps > 2000:
                raise ValidationError(
                    {"tax_rate_bps": "Must be between 0 and 2000."}
                )
            tenant_fields["tax_rate_bps"] = tax_rate_bps

        if "require_paid_in_full_at_pickup" in request.data:
            tenant_fields["require_paid_in_full_at_pickup"] = bool(
                request.data.get("require_paid_in_full_at_pickup")
            )
        if "default_ready_hour" in request.data:
            try:
                default_ready_hour = int(request.data.get("default_ready_hour"))
            except Exception as exc:
                raise ValidationError(
                    {"default_ready_hour": "Must be an integer."}
                ) from exc
            if default_ready_hour < 0 or default_ready_hour > 23:
                raise ValidationError(
                    {"default_ready_hour": "Must be between 0 and 23."}
                )
            tenant_fields["default_ready_hour"] = default_ready_hour
        if "default_due_days" in request.data:
            try:
                default_due_days = int(request.data.get("default_due_days"))
            except Exception as exc:
                raise ValidationError(
                    {"default_due_days": "Must be an integer."}
                ) from exc
            if default_due_days < 0:
                raise ValidationError(
                    {"default_due_days": "Must be >= 0."}
                )
            tenant_fields["default_turnaround_days"] = default_due_days

        with transaction.atomic():
            tenant = Tenant.objects.create(**tenant_fields)

            membership = TenantMembership.objects.create(
                tenant=tenant,
                user=request.user,
                role=TenantMembership.Role.OWNER_ADMIN,
                is_active=True,
            )
            record_membership_event(
                tenant=tenant,
                actor=request.user,
                subject_user=request.user,
                action=TenantMembershipEvent.Action.CREATED,
                new_role=membership.role,
                is_active_after=membership.is_active,
            )

            for key, field_name in (
                ("collects_tax", "collects_tax"),
                ("tax_rate_bps", "tax_rate_bps"),
                ("require_paid_in_full_at_pickup", "require_paid_in_full_at_pickup"),
                ("default_ready_hour", "default_ready_hour"),
                ("default_turnaround_days", "default_turnaround_days"),
            ):
                if field_name not in tenant_fields:
                    continue
                field = Tenant._meta.get_field(field_name)
                default_value = field.default
                new_value = getattr(tenant, field_name)
                if new_value != default_value:
                    config_events.append(
                        TenantConfigEvent(
                            tenant=tenant,
                            actor=request.user,
                            key=field_name,
                            old_value=str(default_value),
                            new_value=str(new_value),
                        )
                    )

            if config_events:
                TenantConfigEvent.objects.bulk_create(config_events)

        return Response(
            {
                "tenant": {"id": tenant.id, "slug": tenant.slug, "name": tenant.name},
                "membership": {
                    "user_id": request.user.id,
                    "role": membership.role,
                    "is_active": membership.is_active,
                },
            },
            status=201,
        )


class TenantMembershipsView(APIView):
    permission_classes = [IsTenantMember]

    def _require_admin(self, request):
        membership = get_active_membership(
            user=request.user, tenant=request.tenant, request=request
        )
        if membership is None:
            raise NotFound()
        if membership.role != TenantMembership.Role.OWNER_ADMIN:
            raise PermissionDenied()
        return membership

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="X-Tenant",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.HEADER,
                required=True,
                description="Tenant slug (e.g. store-1)",
            )
        ],
        responses=TenantMembershipSerializer(many=True),
    )
    def get(self, request):
        self._require_admin(request)
        memberships = (
            TenantMembership.objects.filter(tenant=request.tenant)
            .select_related("user")
            .order_by("created_at", "id")
        )
        return Response(TenantMembershipSerializer(memberships, many=True).data)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="X-Tenant",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.HEADER,
                required=True,
                description="Tenant slug (e.g. store-1)",
            )
        ],
        request=TenantMembershipCreateSerializer,
        responses=TenantMembershipSerializer,
    )
    def post(self, request):
        self._require_admin(request)
        serializer = TenantMembershipCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        User = get_user_model()
        user = User.objects.filter(username=data["username"]).first()

        if user is None:
            raise ValidationError({"username": "User not found."})

        is_active = data.get("is_active", True)
        membership, created = TenantMembership.objects.get_or_create(
            tenant=request.tenant,
            user=user,
            defaults={"role": data["role"], "is_active": is_active},
        )
        if created:
            record_membership_event(
                tenant=request.tenant,
                actor=request.user,
                subject_user=user,
                action=TenantMembershipEvent.Action.CREATED,
                new_role=membership.role,
                is_active_after=membership.is_active,
            )
        else:
            before_role = membership.role
            before_active = membership.is_active
            if membership.role != data["role"]:
                membership.role = data["role"]
            if membership.is_active != is_active:
                membership.is_active = is_active
            if membership.role != before_role or membership.is_active != before_active:
                membership.save(update_fields=["role", "is_active"])
                if membership.role != before_role:
                    record_membership_event(
                        tenant=request.tenant,
                        actor=request.user,
                        subject_user=user,
                        action=TenantMembershipEvent.Action.ROLE_CHANGED,
                        old_role=before_role,
                        new_role=membership.role,
                        is_active_before=before_active,
                        is_active_after=membership.is_active,
                    )
                if membership.is_active != before_active:
                    record_membership_event(
                        tenant=request.tenant,
                        actor=request.user,
                        subject_user=user,
                        action=TenantMembershipEvent.Action.REACTIVATED
                        if membership.is_active
                        else TenantMembershipEvent.Action.DEACTIVATED,
                        old_role=before_role,
                        new_role=membership.role,
                        is_active_before=before_active,
                        is_active_after=membership.is_active,
                    )

        return Response(
            TenantMembershipSerializer(membership).data,
            status=201 if created else 200,
        )


class TenantMembershipDetailView(APIView):
    permission_classes = [IsTenantMember]

    def _require_admin(self, request):
        membership = get_active_membership(
            user=request.user, tenant=request.tenant, request=request
        )
        if membership is None:
            raise NotFound()
        if membership.role != TenantMembership.Role.OWNER_ADMIN:
            raise PermissionDenied()
        return membership

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="X-Tenant",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.HEADER,
                required=True,
                description="Tenant slug (e.g. store-1)",
            ),
            OpenApiParameter(
                name="user_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                required=True,
                description="User id for membership update.",
            ),
        ],
        request=TenantMembershipUpdateSerializer,
        responses=TenantMembershipSerializer,
    )
    def patch(self, request, user_id: int):
        self._require_admin(request)
        serializer = TenantMembershipUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        membership = TenantMembership.objects.filter(
            tenant=request.tenant, user_id=user_id
        ).first()
        if membership is None:
            raise NotFound()

        before_role = membership.role
        before_active = membership.is_active
        new_role = data.get("role", membership.role)
        new_active = data.get("is_active", membership.is_active)

        if membership.role == TenantMembership.Role.OWNER_ADMIN and membership.is_active and (
            new_role != TenantMembership.Role.OWNER_ADMIN or not new_active
        ):
            if active_owner_admin_count(tenant=request.tenant) <= 1:
                raise ValidationError(
                    {"detail": "Cannot remove the last active OWNER_ADMIN."}
                )

        membership.role = new_role
        membership.is_active = new_active
        membership.save(update_fields=["role", "is_active"])

        if before_role != membership.role:
            record_membership_event(
                tenant=request.tenant,
                actor=request.user,
                subject_user=membership.user,
                action=TenantMembershipEvent.Action.ROLE_CHANGED,
                old_role=before_role,
                new_role=membership.role,
                is_active_before=before_active,
                is_active_after=membership.is_active,
            )
        if before_active != membership.is_active:
            record_membership_event(
                tenant=request.tenant,
                actor=request.user,
                subject_user=membership.user,
                action=TenantMembershipEvent.Action.REACTIVATED
                if membership.is_active
                else TenantMembershipEvent.Action.DEACTIVATED,
                old_role=before_role,
                new_role=membership.role,
                is_active_before=before_active,
                is_active_after=membership.is_active,
            )

        return Response(TenantMembershipSerializer(membership).data)


class TenantInvitesView(APIView):
    permission_classes = [IsTenantMember]

    def _require_admin(self, request):
        membership = get_active_membership(
            user=request.user, tenant=request.tenant, request=request
        )
        if membership is None:
            raise NotFound()
        if membership.role != TenantMembership.Role.OWNER_ADMIN:
            raise PermissionDenied()
        return membership

    def get(self, request):
        self._require_admin(request)
        invites = (
            TenantInvite.objects.filter(tenant=request.tenant)
            .order_by("-created_at")
        )
        return Response(TenantInviteSerializer(invites, many=True).data)

    def post(self, request):
        self._require_admin(request)
        serializer = TenantInviteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()

        now = timezone.now()
        token = generate_invite_token()
        token_hash = hash_invite_token(token)
        expires_at = now + timedelta(days=7)

        with transaction.atomic():
            invite = (
                TenantInvite.objects.filter(
                    tenant=request.tenant,
                    email=email,
                    accepted_at__isnull=True,
                    revoked_at__isnull=True,
                    expires_at__gt=now,
                )
                .first()
            )
            if invite:
                invite.token_hash = token_hash
                invite.expires_at = expires_at
                invite.save(update_fields=["token_hash", "expires_at"])
                TenantInviteEvent.objects.create(
                    tenant=request.tenant,
                    actor=request.user,
                    email=email,
                    event_type=TenantInviteEvent.EventType.RESENT,
                )
                return Response(
                    {
                        "id": invite.id,
                        "email": invite.email,
                        "expires_at": invite.expires_at,
                        "token": token,
                    },
                    status=201,
                )

            invite = TenantInvite.objects.create(
                tenant=request.tenant,
                email=email,
                role=TenantInvite.Role.OPERATOR,
                token_hash=token_hash,
                expires_at=expires_at,
                created_by=request.user,
            )
            TenantInviteEvent.objects.create(
                tenant=request.tenant,
                actor=request.user,
                email=email,
                event_type=TenantInviteEvent.EventType.CREATED,
            )

        return Response(
            {
                "id": invite.id,
                "email": invite.email,
                "expires_at": invite.expires_at,
                "token": token,
            },
            status=201,
        )


class TenantInviteRevokeView(APIView):
    permission_classes = [IsTenantMember]

    def _require_admin(self, request):
        membership = get_active_membership(
            user=request.user, tenant=request.tenant, request=request
        )
        if membership is None:
            raise NotFound()
        if membership.role != TenantMembership.Role.OWNER_ADMIN:
            raise PermissionDenied()
        return membership

    def post(self, request, invite_id: int):
        self._require_admin(request)
        invite = TenantInvite.objects.filter(
            tenant=request.tenant, id=invite_id
        ).first()
        if invite is None:
            raise NotFound()

        if not invite.is_active:
            raise ValidationError({"detail": "Invite is not active."})

        with transaction.atomic():
            invite.mark_revoked()
            TenantInviteEvent.objects.create(
                tenant=request.tenant,
                actor=request.user,
                email=invite.email,
                event_type=TenantInviteEvent.EventType.REVOKED,
            )

        return Response(
            {
                "id": invite.id,
                "email": invite.email,
                "revoked_at": invite.revoked_at,
            }
        )


class InviteAcceptView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = InviteAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        token = data["token"]
        token_hash = hash_invite_token(token)
        now = timezone.now()

        invite = TenantInvite.objects.filter(token_hash=token_hash).first()
        if (
            invite is None
            or invite.accepted_at is not None
            or invite.revoked_at is not None
            or invite.expires_at <= now
        ):
            raise ValidationError({"detail": "Invalid or expired invite token."})

        if invite.role != TenantInvite.Role.OPERATOR:
            raise ValidationError({"detail": "Invalid invite token."})

        User = get_user_model()
        email = invite.email.strip().lower()

        with transaction.atomic():
            user = User.objects.filter(email__iexact=email).first()
            created_user = False
            if user is None:
                base_username = email.split("@", 1)[0]
                candidate = base_username or "user"
                suffix = 1
                while User.objects.filter(username=candidate).exists():
                    suffix += 1
                    candidate = f"{base_username}{suffix}"
                user = User.objects.create_user(
                    username=candidate,
                    email=email,
                    first_name=data.get("first_name", ""),
                    last_name=data.get("last_name", ""),
                )
                created_user = True

            user.set_password(data["password"])
            if not user.is_active:
                user.is_active = True
            update_fields = ["password", "is_active"]
            if created_user:
                update_fields.extend(["first_name", "last_name", "email"])
            else:
                if "first_name" in data:
                    user.first_name = data.get("first_name", "")
                    update_fields.append("first_name")
                if "last_name" in data:
                    user.last_name = data.get("last_name", "")
                    update_fields.append("last_name")
                if not user.email:
                    user.email = email
                    update_fields.append("email")
            user.save(update_fields=update_fields)

            membership, membership_created = TenantMembership.objects.get_or_create(
                tenant=invite.tenant,
                user=user,
                defaults={
                    "role": TenantMembership.Role.OPERATOR,
                    "is_active": True,
                },
            )
            before_active = membership.is_active
            if not membership_created and not membership.is_active:
                membership.is_active = True
                membership.save(update_fields=["is_active"])

            invite.accepted_at = now
            invite.save(update_fields=["accepted_at"])

            TenantInviteEvent.objects.create(
                tenant=invite.tenant,
                actor=None,
                email=invite.email,
                event_type=TenantInviteEvent.EventType.ACCEPTED,
            )

            if membership_created:
                record_membership_event(
                    tenant=invite.tenant,
                    actor=None,
                    subject_user=user,
                    action=TenantMembershipEvent.Action.CREATED,
                    new_role=membership.role,
                    is_active_after=membership.is_active,
                    metadata={"source": "invite_accept"},
                )
            elif not membership_created and before_active is False and membership.is_active is True:
                record_membership_event(
                    tenant=invite.tenant,
                    actor=None,
                    subject_user=user,
                    action=TenantMembershipEvent.Action.REACTIVATED,
                    old_role=membership.role,
                    new_role=membership.role,
                    is_active_before=False,
                    is_active_after=True,
                    metadata={"source": "invite_accept"},
                )

        return Response(
            {"status": "accepted", "tenant_slug": invite.tenant.slug, "email": email}
        )
