from django.urls import path
from rest_framework.routers import DefaultRouter

from .auth_views import RegistrationView
from .views import DashboardView, UserViewSet

router = DefaultRouter()

router.register("users", UserViewSet, basename="users")

urlpatterns = [
    path("register/", RegistrationView.as_view(), name="user-register"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
] + router.urls