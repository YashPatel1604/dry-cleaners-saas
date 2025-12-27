from rest_framework.routers import DefaultRouter
from .views import InventoryItemViewSet

router = DefaultRouter()
router.register(r"inventory-items", InventoryItemViewSet,
                basename="inventory-items")

urlpatterns = router.urls
