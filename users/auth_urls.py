from django.urls import path

from .auth_views import (
    CurrentUserView,
    LoginView,
    LogoutView,
    RegistrationView,
    csrf_token_view,
)

urlpatterns = [
    path("csrf/", csrf_token_view, name="auth-csrf"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", CurrentUserView.as_view(), name="auth-current-user"),
]
