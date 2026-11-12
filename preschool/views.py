
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from .models import (
    SchoolYear,
    Classroom,
    Guardian,
    Child,
    ChildGuardian,
    Enrollment,
    Attendance,
    TeacherAttendance,
    TeacherAbsenceRequest,
    ClassSession,
    CourseSupport,
    StudentAssessment,
)

from .serializers import (
    SchoolYearSerializer,
    ClassroomSerializer,
    GuardianSerializer,
    ChildSerializer,
    ChildGuardianSerializer,
    EnrollmentSerializer,
    AttendanceSerializer,
    TeacherAttendanceSerializer,
    TeacherAbsenceRequestSerializer,
    ClassSessionSerializer,
    CourseSupportSerializer,
    StudentAssessmentSerializer,
    PreschoolTeacherCreateSerializer,
    PreschoolTeacherSerializer,
)

User = get_user_model()


ACTION_NAMES = {
    "list": "read",
    "retrieve": "read",
    "create": "create",
    "update": "update",
    "partial_update": "update",
    "destroy": "delete",
    "approve": "approve",
    "reject": "approve",
    "justify": "submit",
    "review_justification": "approve",
}


class PreschoolRolePermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        role = user.role
        action_name = ACTION_NAMES.get(getattr(view, "action", None))
        if action_name is None:
            return False

        if role in {"SECRETARY", "PDG", "DIRECTOR"}:
            return action_name == "read"

        if role not in {"STAFF", "SERVICE_MANAGER"}:
            return False
        if user.service != "PRESCHOOL":
            return False

        allowed = getattr(view, "role_actions", {}).get(role, set())
        return action_name in allowed

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role in {"SECRETARY", "PDG", "DIRECTOR"}:
            return True
        if user.role == "SERVICE_MANAGER":
            return user.service == "PRESCHOOL"
        return view.object_belongs_to_teacher(obj, user)


class PreschoolBaseViewSet(viewsets.ModelViewSet):
    """
    Accès limité au service Préscolaire, avec consultation en lecture seule
    pour le SG, le PDG et la direction.
    """

    permission_classes = [IsAuthenticated, PreschoolRolePermission]
    role_actions = {
        "SERVICE_MANAGER": {"read", "create", "update", "delete"},
        "STAFF": {"read"},
    }

    def object_belongs_to_teacher(self, obj, user):
        return True


class SchoolYearViewSet(PreschoolBaseViewSet):
    queryset = SchoolYear.objects.all()
    serializer_class = SchoolYearSerializer


class ClassroomViewSet(PreschoolBaseViewSet):
    queryset = Classroom.objects.select_related("teacher").all()
    serializer_class = ClassroomSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == "STAFF":
            queryset = queryset.filter(teacher=self.request.user)
        return queryset

    def object_belongs_to_teacher(self, obj, user):
        return obj.teacher_id == user.id

    def perform_create(self, serializer):
        teacher = serializer.validated_data.get("teacher")

        if teacher and teacher.service != "PRESCHOOL":
            raise ValidationError({
                "teacher": "Cet enseignant n'appartient pas au Préscolaire."
            })

        serializer.save()

    def perform_update(self, serializer):
        teacher = serializer.validated_data.get(
            "teacher",
            getattr(serializer.instance, "teacher", None)
        )

        if teacher and teacher.service != "PRESCHOOL":
            raise ValidationError({
                "teacher": "Cet enseignant n'appartient pas au Préscolaire."
            })

        serializer.save()


class GuardianViewSet(PreschoolBaseViewSet):
    queryset = Guardian.objects.all()
    serializer_class = GuardianSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == "STAFF":
            queryset = queryset.filter(
                children__enrollments__classroom__teacher=self.request.user,
                children__enrollments__is_active=True,
            ).distinct()
        return queryset

    def object_belongs_to_teacher(self, obj, user):
        return obj.children.filter(
            enrollments__classroom__teacher=user,
            enrollments__is_active=True,
        ).exists()


class ChildViewSet(PreschoolBaseViewSet):
    queryset = Child.objects.prefetch_related("guardians").all()
    serializer_class = ChildSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == "STAFF":
            queryset = queryset.filter(
                enrollments__classroom__teacher=self.request.user,
                enrollments__is_active=True,
            ).distinct()
        return queryset

    def object_belongs_to_teacher(self, obj, user):
        return obj.enrollments.filter(
            classroom__teacher=user,
            is_active=True,
        ).exists()


class ChildGuardianViewSet(PreschoolBaseViewSet):
    queryset = ChildGuardian.objects.select_related(
        "child",
        "guardian",
    ).all()

    serializer_class = ChildGuardianSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == "STAFF":
            queryset = queryset.filter(
                child__enrollments__classroom__teacher=self.request.user,
                child__enrollments__is_active=True,
            ).distinct()
        return queryset

    def object_belongs_to_teacher(self, obj, user):
        return obj.child.enrollments.filter(
            classroom__teacher=user,
            is_active=True,
        ).exists()


class EnrollmentViewSet(PreschoolBaseViewSet):
    queryset = Enrollment.objects.select_related(
        "child",
        "classroom",
        "school_year",
    ).all()

    serializer_class = EnrollmentSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == "STAFF":
            queryset = queryset.filter(classroom__teacher=self.request.user)
        return queryset

    def object_belongs_to_teacher(self, obj, user):
        return obj.classroom.teacher_id == user.id


class AttendanceViewSet(PreschoolBaseViewSet):
    queryset = Attendance.objects.select_related(
        "enrollment",
        "enrollment__child",
        "enrollment__classroom",
        "enrollment__school_year",
        "recorded_by",
    ).all()

    serializer_class = AttendanceSerializer
    role_actions = {
        "SERVICE_MANAGER": {"read", "create", "update", "delete", "approve"},
        "STAFF": {"read", "create", "update", "submit"},
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == "STAFF":
            queryset = queryset.filter(
                enrollment__classroom__teacher=self.request.user
            )
        return queryset

    def object_belongs_to_teacher(self, obj, user):
        return obj.enrollment.classroom.teacher_id == user.id

    def perform_create(self, serializer):
        enrollment = serializer.validated_data.get("enrollment")

        if not enrollment.is_active:
            raise ValidationError({
                "enrollment": "Cette inscription n'est plus active."
            })
        if (
            self.request.user.role == "STAFF"
            and serializer.validated_data.get("status")
            == Attendance.Status.JUSTIFIED
        ):
            raise PermissionDenied(
                "Seul le responsable peut approuver une justification."
            )
        if (
            self.request.user.role == "STAFF"
            and enrollment.classroom.teacher_id != self.request.user.id
        ):
            raise PermissionDenied(
                "Vous ne pouvez déclarer la présence que des élèves de votre classe."
            )

        serializer.save(recorded_by=self.request.user)

    def perform_update(self, serializer):
        enrollment = serializer.validated_data.get(
            "enrollment",
            serializer.instance.enrollment,
        )
        status_value = serializer.validated_data.get(
            "status",
            serializer.instance.status,
        )
        if (
            self.request.user.role == "STAFF"
            and status_value == Attendance.Status.JUSTIFIED
        ):
            raise PermissionDenied(
                "Seul le responsable peut approuver une justification."
            )
        if (
            self.request.user.role == "STAFF"
            and enrollment.classroom.teacher_id != self.request.user.id
        ):
            raise PermissionDenied(
                "Vous ne pouvez modifier que la présence des élèves de votre classe."
            )
        serializer.save(recorded_by=self.request.user)

    @action(detail=True, methods=["post"])
    def justify(self, request, pk=None):
        attendance = self.get_object()
        if attendance.status not in {
            Attendance.Status.ABSENT,
            Attendance.Status.LATE,
        }:
            raise ValidationError({
                "status": "Une justification ne peut être jointe qu'à une absence ou un retard."
            })
        if attendance.justification_status == Attendance.JustificationStatus.SUBMITTED:
            raise ValidationError({
                "justification_message": "Une justification est déjà en attente de validation."
            })
        message = request.data.get("justification_message")
        if not isinstance(message, str) or not message.strip():
            raise ValidationError({
                "justification_message": "Le message de justification est obligatoire."
            })
        attendance.justification_message = message.strip()
        attendance.justification_status = Attendance.JustificationStatus.SUBMITTED
        attendance.justification_response = ""
        attendance.justification_reviewed_by = None
        attendance.save(update_fields=[
            "justification_message",
            "justification_status",
            "justification_response",
            "justification_reviewed_by",
        ])
        return Response(self.get_serializer(attendance).data)

    @action(
        detail=True,
        methods=["post"],
        url_path="review-justification",
    )
    def review_justification(self, request, pk=None):
        attendance = self.get_object()
        if attendance.justification_status != Attendance.JustificationStatus.SUBMITTED:
            raise ValidationError({
                "justification_status": "Aucune justification n'attend de validation."
            })
        decision = request.data.get("decision")
        if decision not in {"APPROVED", "REJECTED"}:
            raise ValidationError({
                "decision": "Choisissez APPROVED ou REJECTED."
            })
        response_message = request.data.get("manager_message", "")
        if not isinstance(response_message, str):
            raise ValidationError({
                "manager_message": "Le message doit être un texte."
            })
        if decision == "REJECTED" and not response_message.strip():
            raise ValidationError({
                "manager_message": "Un motif est obligatoire pour rejeter la justification."
            })
        attendance.justification_status = (
            Attendance.JustificationStatus.APPROVED
            if decision == "APPROVED"
            else Attendance.JustificationStatus.REJECTED
        )
        if decision == "APPROVED":
            attendance.status = Attendance.Status.JUSTIFIED
        attendance.justification_response = response_message
        attendance.justification_reviewed_by = request.user
        attendance.save(update_fields=[
            "status",
            "justification_status",
            "justification_response",
            "justification_reviewed_by",
        ])
        return Response(self.get_serializer(attendance).data)


class PreschoolTeacherViewSet(PreschoolBaseViewSet):
    queryset = User.objects.filter(
        service="PRESCHOOL",
        role="STAFF",
    ).order_by("last_name", "first_name")
    serializer_class = PreschoolTeacherSerializer
    role_actions = {
        "SERVICE_MANAGER": {"read", "create", "update", "delete"},
        "STAFF": {"read"},
    }

    def get_serializer_class(self):
        if self.action == "create":
            return PreschoolTeacherCreateSerializer
        return super().get_serializer_class()

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])
        Classroom.objects.filter(teacher=instance).update(teacher=None)


class TeacherAttendanceViewSet(PreschoolBaseViewSet):
    queryset = TeacherAttendance.objects.select_related(
        "teacher",
        "classroom",
        "recorded_by",
    ).all()
    serializer_class = TeacherAttendanceSerializer
    role_actions = {
        "SERVICE_MANAGER": {"read", "create", "update", "delete"},
        "STAFF": {"read", "create", "update"},
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == "STAFF":
            queryset = queryset.filter(
                teacher=self.request.user,
                classroom__teacher=self.request.user,
            )
        return queryset

    def object_belongs_to_teacher(self, obj, user):
        return obj.teacher_id == user.id and obj.classroom.teacher_id == user.id

    def perform_create(self, serializer):
        teacher = serializer.validated_data["teacher"]
        classroom = serializer.validated_data["classroom"]
        self.ensure_teacher_can_record(teacher, classroom)
        serializer.save(recorded_by=self.request.user)

    def perform_update(self, serializer):
        teacher = serializer.validated_data.get(
            "teacher",
            serializer.instance.teacher,
        )
        classroom = serializer.validated_data.get(
            "classroom",
            serializer.instance.classroom,
        )
        self.ensure_teacher_can_record(teacher, classroom)
        serializer.save(recorded_by=self.request.user)

    def ensure_teacher_can_record(self, teacher, classroom):
        if (
            teacher.service != "PRESCHOOL"
            or teacher.role != "STAFF"
            or not teacher.is_active
        ):
            raise ValidationError({
                "teacher": "Sélectionnez un enseignant actif du Préscolaire."
            })
        if classroom.teacher_id != teacher.id:
            raise ValidationError({
                "classroom": "L'enseignant n'est pas affecté à cette classe."
            })
        if (
            self.request.user.role == "STAFF"
            and teacher.id != self.request.user.id
        ):
            raise PermissionDenied(
                "Vous ne pouvez déclarer que votre propre présence."
            )


class TeacherAbsenceRequestViewSet(PreschoolBaseViewSet):
    queryset = TeacherAbsenceRequest.objects.select_related(
        "teacher",
        "reviewed_by",
    ).all()
    serializer_class = TeacherAbsenceRequestSerializer
    role_actions = {
        "SERVICE_MANAGER": {"read", "update", "approve"},
        "STAFF": {"read", "create", "update"},
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == "STAFF":
            queryset = queryset.filter(teacher=self.request.user)
        return queryset

    def object_belongs_to_teacher(self, obj, user):
        return obj.teacher_id == user.id

    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user)

    def perform_update(self, serializer):
        if self.request.user.role != "STAFF":
            raise PermissionDenied(
                "Utilisez l'action d'approbation pour traiter cette demande."
            )
        if serializer.instance.status != TeacherAbsenceRequest.Status.SUBMITTED:
            raise ValidationError(
                "Une demande déjà traitée ne peut plus être modifiée."
            )
        serializer.save()

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        absence_request = self.get_object()
        if absence_request.status != TeacherAbsenceRequest.Status.SUBMITTED:
            return Response(
                {"detail": "Cette demande a déjà été traitée."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        decision = request.data.get("decision")
        if decision not in {
            TeacherAbsenceRequest.Status.APPROVED,
            TeacherAbsenceRequest.Status.REJECTED,
        }:
            raise ValidationError({
                "decision": "Choisissez APPROVED ou REJECTED."
            })
        manager_message = request.data.get("manager_message", "")
        if not isinstance(manager_message, str):
            raise ValidationError({
                "manager_message": "Le message doit être un texte."
            })
        if decision == TeacherAbsenceRequest.Status.REJECTED and not manager_message.strip():
            raise ValidationError({
                "manager_message": "Un motif est obligatoire pour rejeter la demande."
            })
        absence_request.status = decision
        absence_request.manager_message = manager_message
        absence_request.reviewed_by = request.user
        absence_request.reviewed_at = timezone.now()
        absence_request.save(update_fields=[
            "status",
            "manager_message",
            "reviewed_by",
            "reviewed_at",
        ])
        return Response(self.get_serializer(absence_request).data)


class ClassSessionViewSet(PreschoolBaseViewSet):
    queryset = ClassSession.objects.select_related(
        "classroom",
        "teacher",
        "created_by",
    ).all()
    serializer_class = ClassSessionSerializer
    role_actions = {
        "SERVICE_MANAGER": {"read", "create", "update", "delete"},
        "STAFF": {"read"},
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == "STAFF":
            queryset = queryset.filter(
                teacher=self.request.user,
                classroom__teacher=self.request.user,
            )
        return queryset

    def object_belongs_to_teacher(self, obj, user):
        return obj.teacher_id == user.id and obj.classroom.teacher_id == user.id

    def perform_create(self, serializer):
        classroom = serializer.validated_data["classroom"]
        if (
            classroom.teacher_id != serializer.validated_data["teacher"].id
        ):
            raise ValidationError({
                "teacher": "L'enseignant doit être affecté à cette classe."
            })
        serializer.save(created_by=self.request.user)


class CourseSupportViewSet(PreschoolBaseViewSet):
    queryset = CourseSupport.objects.select_related(
        "classroom",
        "teacher",
    ).all()
    serializer_class = CourseSupportSerializer
    role_actions = {
        "SERVICE_MANAGER": {"read", "create", "update", "delete"},
        "STAFF": {"read", "create", "update", "delete"},
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == "STAFF":
            queryset = queryset.filter(
                teacher=self.request.user,
                classroom__teacher=self.request.user,
            )
        return queryset

    def object_belongs_to_teacher(self, obj, user):
        return obj.teacher_id == user.id and obj.classroom.teacher_id == user.id

    def perform_create(self, serializer):
        classroom = serializer.validated_data["classroom"]
        if self.request.user.role == "STAFF":
            if classroom.teacher_id != self.request.user.id:
                raise PermissionDenied(
                    "Vous ne pouvez ajouter un support qu'à votre classe."
                )
            teacher = self.request.user
        else:
            teacher = classroom.teacher
            if teacher is None:
                raise ValidationError({
                    "classroom": "Affectez un enseignant à cette classe avant d'ajouter un support."
                })
        serializer.save(teacher=teacher)

    def perform_update(self, serializer):
        classroom = serializer.validated_data.get(
                "classroom",
                serializer.instance.classroom,
        )
        if self.request.user.role == "STAFF":
                if classroom.teacher_id != self.request.user.id:
                    raise PermissionDenied(
                        "Vous ne pouvez déplacer un support que dans votre classe."
                    )
                serializer.save()
                return
        teacher = classroom.teacher
        if teacher is None:
                raise ValidationError({
                    "classroom": "Affectez un enseignant à cette classe avant d'ajouter un support."
                })
        serializer.save(teacher=teacher)


class StudentAssessmentViewSet(PreschoolBaseViewSet):
    queryset = StudentAssessment.objects.select_related(
        "enrollment",
        "enrollment__child",
        "enrollment__classroom",
        "recorded_by",
    ).all()
    serializer_class = StudentAssessmentSerializer
    role_actions = {
        "SERVICE_MANAGER": {"read", "create", "update", "delete"},
        "STAFF": {"read", "create", "update"},
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == "STAFF":
            queryset = queryset.filter(
                enrollment__classroom__teacher=self.request.user
            )
        return queryset

    def object_belongs_to_teacher(self, obj, user):
        return obj.enrollment.classroom.teacher_id == user.id

    def perform_create(self, serializer):
        enrollment = serializer.validated_data["enrollment"]
        if not enrollment.is_active:
            raise ValidationError({
                "enrollment": "Cette inscription n'est plus active."
            })
        if (
            self.request.user.role == "STAFF"
            and enrollment.classroom.teacher_id != self.request.user.id
        ):
            raise PermissionDenied(
                "Vous ne pouvez évaluer que les élèves de vos classes."
            )
        serializer.save(recorded_by=self.request.user)

    def perform_update(self, serializer):
        enrollment = serializer.validated_data.get(
            "enrollment",
            serializer.instance.enrollment,
        )
        if (
            self.request.user.role == "STAFF"
            and enrollment.classroom.teacher_id != self.request.user.id
        ):
            raise PermissionDenied(
                "Vous ne pouvez évaluer que les élèves de vos classes."
            )
        serializer.save(recorded_by=self.request.user)
