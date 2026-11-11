from rest_framework.routers import DefaultRouter

from .views import ClientViewSet, ContractViewSet, ServiceOrderViewSet

router = DefaultRouter()

router.register("clients", ClientViewSet)
router.register("contracts", ContractViewSet)
router.register("service-orders", ServiceOrderViewSet)

urlpatterns = router.urls