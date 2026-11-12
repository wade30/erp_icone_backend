
from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.password_validation import validate_password

from .models import User


# ============================================================
# SERVICES ACCESSIBLES DEPUIS L'INSCRIPTION PUBLIQUE
# ============================================================

PUBLIC_SERVICES = [
    User.Service.INSTITUTE,
    User.Service.INCUBATOR,
    User.Service.MARKETING,
    User.Service.ORIENTATION,
    User.Service.PRESCHOOL,
]


# ============================================================
# VALIDATION COMMUNE DES MOTS DE PASSE
# ============================================================

def validate_user_password(password, user=None):
    try:
        validate_password(password, user=user)
    except DjangoValidationError as error:
        raise serializers.ValidationError({
            "password": error.messages
        }) from error


# ============================================================
# 1. INSCRIPTION PUBLIQUE
# ============================================================

class UserRegistrationSerializer(serializers.ModelSerializer):

    email = serializers.EmailField(required=True)

    password = serializers.CharField(
        write_only=True,
        min_length=8
    )

    service = serializers.ChoiceField(
        choices=[
            (service.value, service.label)
            for service in User.Service
            if service.value in PUBLIC_SERVICES
        ],
        required=True
    )

    telephone = serializers.CharField(
        max_length=30,
        required=False,
        allow_blank=True
    )

    fonction = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "telephone",
            "fonction",
            "service",
            "password",
        ]

    def validate_email(self, value):
        value = value.strip().lower()

        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "Cette adresse e-mail est déjà utilisée."
            )

        return value

    def validate(self, attrs):
        user = User(
            username=attrs.get("username"),
            email=attrs.get("email"),
            first_name=attrs.get("first_name"),
            last_name=attrs.get("last_name"),
        )

        validate_user_password(
            attrs["password"],
            user=user
        )

        return attrs

    def create(self, validated_data):

        password = validated_data.pop("password")

        # Le rôle et l'activation sont imposés par le serveur.
        return User.objects.create_user(
            password=password,
            role=User.Role.STAFF,
            is_active=False,
            **validated_data
        )


# ============================================================
# 2. SERIALIZER DE CONSULTATION ET DE MODIFICATION
# ============================================================

class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User

        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "service",
            "telephone",
            "fonction",
            "is_active",
        ]

        read_only_fields = [
            "id",
            "username",
        ]

    def validate_email(self, value):

        value = value.strip().lower()

        queryset = User.objects.filter(
            email__iexact=value
        )

        if self.instance:
            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if queryset.exists():
            raise serializers.ValidationError(
                "Cette adresse e-mail est déjà utilisée."
            )

        return value


class CurrentUserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "telephone",
            "fonction",
        ]

    def validate(self, attrs):
        unknown_fields = set(self.initial_data) - set(self.fields)
        if unknown_fields:
            raise serializers.ValidationError({
                "detail": (
                    "Seules les informations personnelles peuvent être modifiées."
                )
            })
        return attrs

    def validate_email(self, value):
        value = value.strip().lower()
        queryset = User.objects.filter(email__iexact=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError(
                "Cette adresse e-mail est déjà utilisée."
            )
        return value


# ============================================================
# 3. CRÉATION ADMINISTRATIVE D'UN UTILISATEUR
# ============================================================

class UserCreateSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True,
        min_length=8
    )

    class Meta:
        model = User

        fields = [
            "id",
            "username",
            "email",
            "password",
            "first_name",
            "last_name",
            "role",
            "service",
            "telephone",
            "fonction",
        ]

        read_only_fields = ["id"]

    def validate_email(self, value):

        value = value.strip().lower()

        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "Cette adresse e-mail est déjà utilisée."
            )

        return value

    def validate(self, attrs):

        user = User(
            username=attrs.get("username"),
            email=attrs.get("email"),
            first_name=attrs.get("first_name"),
            last_name=attrs.get("last_name"),
        )

        validate_user_password(
            attrs["password"],
            user=user
        )

        return attrs

    def create(self, validated_data):

        password = validated_data.pop("password")

        return User.objects.create_user(
            password=password,
            **validated_data
        )
