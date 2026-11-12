
from django.contrib.auth import get_user_model
from django.utils import timezone

from rest_framework import serializers

from users.serializers import validate_user_password

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

User = get_user_model()


# ============================================================
# 1. ANNÉES SCOLAIRES
# ============================================================

class SchoolYearSerializer(serializers.ModelSerializer):

    class Meta:
        model = SchoolYear
        fields = "__all__"

    def validate(self, attrs):
        start_date = attrs.get(
            "start_date",
            getattr(self.instance, "start_date", None),
        )

        end_date = attrs.get(
            "end_date",
            getattr(self.instance, "end_date", None),
        )

        if start_date and end_date and end_date <= start_date:
            raise serializers.ValidationError({
                "end_date": (
                    "La date de fin doit être postérieure "
                    "à la date de début."
                )
            })

        return attrs


# ============================================================
# 2. CLASSES
# ============================================================

class ClassroomSerializer(serializers.ModelSerializer):

    teacher_name = serializers.SerializerMethodField()

    class Meta:
        model = Classroom
        fields = "__all__"

    def get_teacher_name(self, obj):
        if obj.teacher:
            return (
                obj.teacher.get_full_name()
                or obj.teacher.username
            )
        return None

    def validate_teacher(self, value):
        if value:
            if value.service != "PRESCHOOL" or value.role != "STAFF":
                raise serializers.ValidationError(
                    "L'enseignant doit être un collaborateur du service Préscolaire."
                )

            if not value.is_active:
                raise serializers.ValidationError(
                    "Cet utilisateur est désactivé."
                )

        return value


# ============================================================
# 3. PARENTS ET TUTEURS
# ============================================================

class GuardianSerializer(serializers.ModelSerializer):

    class Meta:
        model = Guardian
        fields = "__all__"


# ============================================================
# 4. ENFANTS
# ============================================================

class ChildSerializer(serializers.ModelSerializer):

    guardians = serializers.PrimaryKeyRelatedField(
        many=True,
        read_only=True,
    )

    guardian_names = serializers.SerializerMethodField()

    class Meta:
        model = Child
        fields = "__all__"
        read_only_fields = ["created_at"]

    def get_guardian_names(self, obj):
        return [
            str(guardian)
            for guardian in obj.guardians.all()
        ]

    def validate_date_of_birth(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError(
                "La date de naissance ne peut pas être dans le futur."
            )

        return value


# ============================================================
# 5. RELATIONS ENFANTS - PARENTS
# ============================================================

class ChildGuardianSerializer(serializers.ModelSerializer):

    child_name = serializers.SerializerMethodField()
    guardian_name = serializers.SerializerMethodField()

    child_matricule = serializers.CharField(
        source="child.matricule",
        read_only=True,
    )

    guardian_telephone = serializers.CharField(
        source="guardian.telephone",
        read_only=True,
    )

    class Meta:
        model = ChildGuardian
        fields = "__all__"

    def get_child_name(self, obj):
        return str(obj.child)

    def get_guardian_name(self, obj):
        return str(obj.guardian)


# ============================================================
# 6. INSCRIPTIONS
# ============================================================

class EnrollmentSerializer(serializers.ModelSerializer):

    child_name = serializers.SerializerMethodField()

    child_matricule = serializers.CharField(
        source="child.matricule",
        read_only=True,
    )

    classroom_name = serializers.SerializerMethodField()

    school_year_name = serializers.CharField(
        source="school_year.name",
        read_only=True,
    )

    class Meta:
        model = Enrollment
        fields = "__all__"

    def get_child_name(self, obj):
        return str(obj.child)

    def get_classroom_name(self, obj):
        return str(obj.classroom)

    def validate(self, attrs):
        registration_fee = attrs.get(
            "registration_fee",
            getattr(self.instance, "registration_fee", 0),
        )

        tuition_fee = attrs.get(
            "tuition_fee",
            getattr(self.instance, "tuition_fee", 0),
        )

        if registration_fee < 0:
            raise serializers.ValidationError({
                "registration_fee": "Les frais ne peuvent pas être négatifs."
            })

        if tuition_fee < 0:
            raise serializers.ValidationError({
                "tuition_fee": "Les frais ne peuvent pas être négatifs."
            })

        return attrs


# ============================================================
# 7. PRÉSENCES
# ============================================================

class AttendanceSerializer(serializers.ModelSerializer):

    child_name = serializers.SerializerMethodField()

    registration_number = serializers.CharField(
        source="enrollment.registration_number",
        read_only=True,
    )

    classroom_name = serializers.SerializerMethodField()

    recorded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = "__all__"
        read_only_fields = [
            "recorded_by",
            "justification_message",
            "justification_status",
            "justification_response",
            "justification_reviewed_by",
        ]

    def get_child_name(self, obj):
        return str(obj.enrollment.child)

    def get_classroom_name(self, obj):
        return str(obj.enrollment.classroom)

    def get_recorded_by_name(self, obj):
        if obj.recorded_by:
            return (
                obj.recorded_by.get_full_name()
                or obj.recorded_by.username
            )

        return None

    def validate_enrollment(self, value):
        if not value.is_active:
            raise serializers.ValidationError(
                "Cette inscription n'est plus active."
            )

        return value


class TeacherAttendanceSerializer(serializers.ModelSerializer):
    teacher = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        default=serializers.CurrentUserDefault(),
    )
    teacher_name = serializers.SerializerMethodField()
    classroom_name = serializers.CharField(
        source="classroom.name",
        read_only=True,
    )
    recorded_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = TeacherAttendance
        fields = "__all__"

    def get_teacher_name(self, obj):
        return obj.teacher.get_full_name() or obj.teacher.username


class TeacherAbsenceRequestSerializer(serializers.ModelSerializer):
    teacher_name = serializers.SerializerMethodField()
    reviewed_by = serializers.PrimaryKeyRelatedField(read_only=True)
    reviewed_at = serializers.DateTimeField(read_only=True)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = TeacherAbsenceRequest
        fields = "__all__"
        read_only_fields = ["teacher", "created_at"]

    def get_teacher_name(self, obj):
        return obj.teacher.get_full_name() or obj.teacher.username

    def validate(self, attrs):
        start_date = attrs.get(
            "start_date",
            getattr(self.instance, "start_date", None),
        )
        end_date = attrs.get(
            "end_date",
            getattr(self.instance, "end_date", None),
        )
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({
                "end_date": "La date de fin doit suivre la date de début."
            })
        if self.instance and self.instance.status != TeacherAbsenceRequest.Status.SUBMITTED:
            raise serializers.ValidationError(
                "Une demande déjà traitée ne peut plus être modifiée."
            )
        return attrs


class ClassSessionSerializer(serializers.ModelSerializer):
    classroom_name = serializers.CharField(
        source="classroom.name",
        read_only=True,
    )
    teacher_name = serializers.SerializerMethodField()
    attendance_status = serializers.SerializerMethodField()

    class Meta:
        model = ClassSession
        fields = "__all__"
        read_only_fields = ["created_by", "created_at"]

    def get_teacher_name(self, obj):
        return obj.teacher.get_full_name() or obj.teacher.username

    def get_attendance_status(self, obj):
        attendance = TeacherAttendance.objects.filter(
            teacher=obj.teacher,
            classroom=obj.classroom,
            date=timezone.localtime(obj.starts_at).date(),
        ).first()
        return attendance.status if attendance else None

    def validate(self, attrs):
        starts_at = attrs.get(
            "starts_at",
            getattr(self.instance, "starts_at", None),
        )
        ends_at = attrs.get(
            "ends_at",
            getattr(self.instance, "ends_at", None),
        )
        classroom = attrs.get(
            "classroom",
            getattr(self.instance, "classroom", None),
        )
        teacher = attrs.get(
            "teacher",
            getattr(self.instance, "teacher", None),
        )
        if starts_at and ends_at and ends_at <= starts_at:
            raise serializers.ValidationError({
                "ends_at": "La fin de séance doit suivre son début."
            })
        if classroom and teacher and classroom.teacher_id != teacher.id:
            raise serializers.ValidationError({
                "teacher": "L'enseignant doit être affecté à cette classe."
            })
        if teacher and (
            teacher.service != "PRESCHOOL"
            or teacher.role != "STAFF"
            or not teacher.is_active
        ):
            raise serializers.ValidationError({
                "teacher": "Sélectionnez un enseignant actif du Préscolaire."
            })
        return attrs


class CourseSupportSerializer(serializers.ModelSerializer):
    classroom_name = serializers.CharField(
        source="classroom.name",
        read_only=True,
    )
    teacher_name = serializers.SerializerMethodField()

    class Meta:
        model = CourseSupport
        fields = "__all__"
        read_only_fields = ["teacher", "created_at"]

    def get_teacher_name(self, obj):
        return obj.teacher.get_full_name() or obj.teacher.username


class StudentAssessmentSerializer(serializers.ModelSerializer):
    child_name = serializers.SerializerMethodField()
    classroom_name = serializers.CharField(
        source="enrollment.classroom.name",
        read_only=True,
    )
    recorded_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = StudentAssessment
        fields = "__all__"

    def get_child_name(self, obj):
        return str(obj.enrollment.child)

    def validate_score(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError(
                "Le niveau doit être compris entre 1 et 5."
            )
        return value


class PreschoolTeacherCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
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
        validate_user_password(attrs["password"], user=user)
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        return User.objects.create_user(
            password=password,
            role=User.Role.STAFF,
            service=User.Service.PRESCHOOL,
            **validated_data,
        )


class PreschoolTeacherSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "telephone",
            "fonction",
            "is_active",
        ]
        read_only_fields = ["id", "username", "email", "is_active"]
