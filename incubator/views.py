from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from users.permissions import ERPModulePermission, ServiceScopedQuerysetMixin

from .models import Entrepreneur, Project, CoachingSession

from .serializers import (
    EntrepreneurSerializer,
    ProjectSerializer,
    CoachingSessionSerializer,
)


class EntrepreneurViewSet(ServiceScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Entrepreneur.objects.all()
    serializer_class = EntrepreneurSerializer
    permission_classes = [IsAuthenticated, ERPModulePermission]
    permission_module = "incubator"


class ProjectViewSet(ServiceScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Project.objects.select_related(
        "entrepreneur"
    ).all()
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, ERPModulePermission]
    permission_module = "incubator"


class CoachingSessionViewSet(ServiceScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = CoachingSession.objects.select_related(
        "project", "coach"
    ).all()
    serializer_class = CoachingSessionSerializer
    permission_classes = [IsAuthenticated, ERPModulePermission]
    permission_module = "incubator"