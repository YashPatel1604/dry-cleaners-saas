from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value: str) -> str:
        return value.strip().lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField()

    def validate_new_password(self, value: str) -> str:
        validate_password(value)
        return value
