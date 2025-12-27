from django.urls import path
from .views import TenantCreateView, TenantMeView

urlpatterns = [
    path("", TenantCreateView.as_view(), name="tenant-create"),
    path("me/", TenantMeView.as_view(), name="tenant-me"),
]
