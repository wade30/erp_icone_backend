from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from users.permissions import ERPModulePermission, ServiceScopedQuerysetMixin

from .models import Course, Learner, Enrollment

from .serializers import (
    CourseSerializer,
    LearnerSerializer,
    EnrollmentSerializer,
)


class CourseViewSet(ServiceScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated, ERPModulePermission]
    permission_module = "institute"


class LearnerViewSet(ServiceScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Learner.objects.all()
    serializer_class = LearnerSerializer
    permission_classes = [IsAuthenticated, ERPModulePermission]
    permission_module = "institute"


class EnrollmentViewSet(ServiceScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Enrollment.objects.select_related(
        "learner", "course"
    ).all()
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated, ERPModulePermission]
    permission_module = "institute"