# payments/urls.py
from rest_framework.routers import DefaultRouter
from .views import PaymentViewSet, AdjustmentViewSet

router = DefaultRouter()
router.register(r"payments", PaymentViewSet, basename="payments")
router.register(r"adjustments", AdjustmentViewSet, basename="adjustments")

urlpatterns = router.urls
