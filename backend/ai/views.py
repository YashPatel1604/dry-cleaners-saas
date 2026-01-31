import json
import os
import urllib.error
import urllib.request

from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from tenants.permissions import IsTenantMember


class AiChatView(APIView):
    permission_classes = [IsTenantMember]

    def post(self, request):
        data = request.data or {}
        messages = data.get("messages")
        if not isinstance(messages, list) or not messages:
            raise ValidationError({"messages": "Provide a list of chat messages."})

        max_messages = int(os.environ.get("OLLAMA_MAX_MESSAGES", "12"))
        trimmed_messages = messages[-max_messages:]

        payload = {
            "model": os.environ.get("OLLAMA_MODEL", "llama3.1"),
            "messages": trimmed_messages,
            "stream": False,
        }

        base_url = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
        url = f"{base_url}/api/chat"

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.URLError as exc:
            raise ValidationError({"detail": "Unable to reach AI provider."}) from exc

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return Response({"content": body})

        content = (
            (payload.get("message") or {}).get("content")
            or payload.get("response")
            or ""
        )
        return Response({"content": content})
