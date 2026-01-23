from rest_framework import serializers
from .models import Customer


class CustomerListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "name", "phone", "email", "created_at"]


class CustomerDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "name", "phone", "email", "notes", "created_at", "updated_at"]


class CustomerCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["name", "phone", "email", "notes"]

    def validate_phone(self, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    def validate_email(self, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().lower()
