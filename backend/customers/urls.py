from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet

router = DefaultRouter()
router.register(r"customers", CustomerViewSet, basename="customers")

urlpatterns = router.urls
