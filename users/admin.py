from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Informations professionnelles", {
            "fields": ("role", "service", "telephone", "fonction")
        }),
    )

    list_display = (
        "username", "email", "first_name",
        "last_name", "role", "service", "is_active"
    )

    list_filter = ("role", "service", "is_active")