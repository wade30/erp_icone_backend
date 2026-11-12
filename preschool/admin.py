
from django.contrib import admin
from .models import (
    SchoolYear,
    Classroom,
    Guardian,
    Child,
    ChildGuardian,
    Enrollment,
    Attendance,
)


@admin.register(SchoolYear)
class SchoolYearAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ("name", "level", "capacity", "teacher", "is_active")
    list_filter = ("level", "is_active")
    search_fields = ("name",)


@admin.register(Guardian)
class GuardianAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "telephone", "email")
    search_fields = ("first_name", "last_name", "telephone")


class ChildGuardianInline(admin.TabularInline):
    model = ChildGuardian
    extra = 1


@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = (
        "matricule",
        "first_name",
        "last_name",
        "date_of_birth",
        "gender",
        "is_active",
    )
    list_filter = ("gender", "is_active")
    search_fields = ("matricule", "first_name", "last_name")
    inlines = [ChildGuardianInline]


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = (
        "registration_number",
        "child",
        "classroom",
        "school_year",
        "enrollment_date",
        "is_active",
    )
    list_filter = ("school_year", "classroom", "is_active")
    search_fields = (
        "registration_number",
        "child__first_name",
        "child__last_name",
    )


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = (
        "enrollment",
        "date",
        "status",
        "arrival_time",
        "departure_time",
    )
    list_filter = ("date", "status")
    search_fields = (
        "enrollment__child__first_name",
        "enrollment__child__last_name",
    )
