
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_GET

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .serializers import (
    CurrentUserProfileSerializer,
    UserRegistrationSerializer,
)


# ============================================================
# 1. RÉCUPÉRATION DU TOKEN CSRF
# ============================================================

@ensure_csrf_cookie
@require_GET
def csrf_token_view(request):
    return JsonResponse({
        "csrfToken": get_token(request)
    })


# ============================================================
# 2. INSCRIPTION
# ============================================================

@method_decorator(csrf_protect, name="dispatch")
class RegistrationView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "registration"

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "detail": (
                    "Votre demande a été enregistrée. Un administrateur doit "
                    "activer votre compte avant votre première connexion."
                )
            },
            status=status.HTTP_201_CREATED,
        )


# ============================================================
# 3. CONNEXION
# ============================================================

@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        if (
            not isinstance(username, str)
            or not isinstance(password, str)
        ):
            return Response(
                {"detail": "Identifiant ou mot de passe invalide."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is None:
            return Response(
                {"detail": "Identifiant ou mot de passe invalide."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        login(request, user)

        return Response(status=status.HTTP_200_OK)


# ============================================================
# 4. UTILISATEUR CONNECTÉ
# ============================================================

class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
                "service": user.service,
                "is_staff": user.is_staff,
                "telephone": user.telephone,
                "fonction": user.fonction,
            }
        )

    def patch(self, request):
        serializer = CurrentUserProfileSerializer(
            request.user,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        user = request.user

        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "service": user.service,
            "is_staff": user.is_staff,
            "telephone": user.telephone,
            "fonction": user.fonction,
        })


# ============================================================
# 5. DÉCONNEXION
# ============================================================

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )
