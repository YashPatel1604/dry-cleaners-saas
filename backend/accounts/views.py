from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

from tenants.models import PasswordResetToken
from tenants.utils import generate_token, hash_token
from .models import PasswordResetEvent
from .serializers import (
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        token = None
        User = get_user_model()
        user = User.objects.filter(email__iexact=email).first()

        with transaction.atomic():
            if user is not None:
                token = generate_token()
                token_hash = hash_token(token)
                expires_at = timezone.now() + timedelta(minutes=30)
                PasswordResetToken.create_for_user(
                    user=user,
                    token_hash=token_hash,
                    expires_at=expires_at,
                )

            PasswordResetEvent.objects.create(
                email=email,
                event_type=PasswordResetEvent.EventType.REQUESTED,
            )

        data = {"status": "ok"}
        if settings.DEBUG and token is not None:
            data["token"] = token
        return Response(data, status=200)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]
        token_hash = hash_token(token)
        now = timezone.now()

        with transaction.atomic():
            reset_token = (
                PasswordResetToken.objects.select_for_update()
                .filter(token_hash=token_hash)
                .first()
            )
            if (
                reset_token is None
                or reset_token.used_at is not None
                or reset_token.expires_at <= now
            ):
                raise ValidationError({"detail": "Invalid or expired reset token."})

            user = reset_token.user
            user.set_password(new_password)
            user.save(update_fields=["password"])

            reset_token.used_at = now
            reset_token.save(update_fields=["used_at"])

            PasswordResetEvent.objects.create(
                email=user.email,
                event_type=PasswordResetEvent.EventType.CONFIRMED,
            )

        return Response({"status": "ok"}, status=200)
