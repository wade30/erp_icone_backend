
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    SchoolYearViewSet,
    ClassroomViewSet,
    GuardianViewSet,
    ChildViewSet,
    ChildGuardianViewSet,
    EnrollmentViewSet,
    AttendanceViewSet,
    PreschoolTeacherViewSet,
    TeacherAttendanceViewSet,
    TeacherAbsenceRequestViewSet,
    ClassSessionViewSet,
    CourseSupportViewSet,
    StudentAssessmentViewSet,
)

router = DefaultRouter()

router.register(
    r"school-years",
    SchoolYearViewSet,
    basename="school-year",
)

router.register(
    r"classrooms",
    ClassroomViewSet,
    basename="classroom",
)

router.register(
    r"guardians",
    GuardianViewSet,
    basename="guardian",
)

router.register(
    r"children",
    ChildViewSet,
    basename="child",
)

router.register(
    r"child-guardians",
    ChildGuardianViewSet,
    basename="child-guardian",
)

router.register(
    r"enrollments",
    EnrollmentViewSet,
    basename="enrollment",
)

router.register(
    r"attendances",
    AttendanceViewSet,
    basename="attendance",
)

router.register(
    r"teachers",
    PreschoolTeacherViewSet,
    basename="preschool-teacher",
)

router.register(
    r"teacher-attendances",
    TeacherAttendanceViewSet,
    basename="teacher-attendance",
)

router.register(
    r"teacher-absence-requests",
    TeacherAbsenceRequestViewSet,
    basename="teacher-absence-request",
)

router.register(
    r"class-sessions",
    ClassSessionViewSet,
    basename="class-session",
)

router.register(
    r"course-supports",
    CourseSupportViewSet,
    basename="course-support",
)

router.register(
    r"assessments",
    StudentAssessmentViewSet,
    basename="student-assessment",
)

urlpatterns = [
    path("", include(router.urls)),
]
