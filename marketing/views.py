from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from users.permissions import ERPModulePermission, ServiceScopedQuerysetMixin

from .models import Client, Contract, ServiceOrder

from .serializers import (
    ClientSerializer,
    ContractSerializer,
    ServiceOrderSerializer,
)


class ClientViewSet(ServiceScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated, ERPModulePermission]
    permission_module = "marketing"


class ContractViewSet(ServiceScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Contract.objects.select_related("client").all()
    serializer_class = ContractSerializer
    permission_classes = [IsAuthenticated, ERPModulePermission]
    permission_module = "marketing"


class ServiceOrderViewSet(ServiceScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ServiceOrder.objects.select_related("contract").all()
    serializer_class = ServiceOrderSerializer
    permission_classes = [IsAuthenticated, ERPModulePermission]
    permission_module = "marketing"