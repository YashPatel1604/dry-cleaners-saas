from django.urls import path

from .views import AiChatView

urlpatterns = [
    path("chat/", AiChatView.as_view(), name="ai-chat"),
]
