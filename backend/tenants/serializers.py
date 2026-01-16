from rest_framework import serializers
from .models import Tenant


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
