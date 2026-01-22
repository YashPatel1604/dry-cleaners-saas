from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Tenant, TenantMembership, TenantInvite


class TenantCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ["name", "slug"]


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = [
            "id",
            "name",
            "slug",
            "is_active",
            "created_at",
            "collects_tax",
            "tax_rate_bps",
        ]


class TenantDefaultsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = [
            "default_turnaround_days",
            "default_ready_hour",
            "default_ready_minute",
            "require_paid_in_full_at_pickup",
            "collects_tax",
            "tax_rate_bps",
        ]

    def validate_default_turnaround_days(self, v):
        if v is None or int(v) < 0 or int(v) > 30:
            raise serializers.ValidationError("Must be between 0 and 30 days.")
        return v

    def validate_default_ready_hour(self, v):
        if v is None or int(v) < 0 or int(v) > 23:
            raise serializers.ValidationError("Must be between 0 and 23.")
        return v

    def validate_default_ready_minute(self, v):
        if v is None or int(v) < 0 or int(v) > 59:
            raise serializers.ValidationError("Must be between 0 and 59.")
        return v

    def validate_tax_rate_bps(self, v):
        if v is None or int(v) < 0 or int(v) > 2000:
            raise serializers.ValidationError("Must be between 0 and 2000.")
        return v


class TenantMembershipUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ["id", "username"]


class TenantMembershipSerializer(serializers.ModelSerializer):
    user = TenantMembershipUserSerializer(read_only=True)

    class Meta:
        model = TenantMembership
        fields = ["id", "user", "role", "is_active", "created_at"]


class TenantMembershipCreateSerializer(serializers.Serializer):
    username = serializers.CharField(required=True, allow_blank=False)
    role = serializers.ChoiceField(choices=TenantMembership.Role.choices)
    is_active = serializers.BooleanField(required=False)


class TenantMembershipUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=TenantMembership.Role.choices, required=False)
    is_active = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if "role" not in attrs and "is_active" not in attrs:
            raise serializers.ValidationError(
                {"detail": "Provide role and/or is_active."}
            )
        return attrs


class TenantInviteCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()


class TenantInviteSerializer(serializers.ModelSerializer):
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = TenantInvite
        fields = [
            "id",
            "email",
            "expires_at",
            "accepted_at",
            "revoked_at",
            "created_at",
            "is_active",
        ]

    def get_is_active(self, obj) -> bool:
        return obj.is_active


class InviteAcceptSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField()
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
