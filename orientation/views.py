from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from users.permissions import ERPModulePermission, ServiceScopedQuerysetMixin

from .models import Beneficiary, Appointment, OrientationRecord

from .serializers import (
    BeneficiarySerializer,
    AppointmentSerializer,
    OrientationRecordSerializer,
)


class BeneficiaryViewSet(ServiceScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Beneficiary.objects.all()
    serializer_class = BeneficiarySerializer
    permission_classes = [IsAuthenticated, ERPModulePermission]
    permission_module = "orientation"


class AppointmentViewSet(ServiceScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Appointment.objects.select_related(
        "beneficiary", "responsible"
    ).all()
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated, ERPModulePermission]
    permission_module = "orientation"


class OrientationRecordViewSet(ServiceScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = OrientationRecord.objects.select_related(
        "beneficiary", "created_by"
    ).all()
    serializer_class = OrientationRecordSerializer
    permission_classes = [IsAuthenticated, ERPModulePermission]
    permission_module = "orientation"