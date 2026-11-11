from rest_framework.routers import DefaultRouter

from .views import (
    BeneficiaryViewSet,
    AppointmentViewSet,
    OrientationRecordViewSet,
)

router = DefaultRouter()

router.register("beneficiaries", BeneficiaryViewSet)
router.register("appointments", AppointmentViewSet)
router.register("records", OrientationRecordViewSet)

urlpatterns = router.urls