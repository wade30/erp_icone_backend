
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class SchoolYear(models.Model):
    name = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Année scolaire"
    )
    start_date = models.DateField(verbose_name="Date de début")
    end_date = models.DateField(verbose_name="Date de fin")
    is_active = models.BooleanField(default=False)

    class Meta:
        ordering = ["-start_date"]
        verbose_name = "Année scolaire"
        verbose_name_plural = "Années scolaires"

    def clean(self):
        if self.end_date <= self.start_date:
            raise ValidationError(
                "La date de fin doit être postérieure à la date de début."
            )

    def __str__(self):
        return self.name


class Classroom(models.Model):

    class Level(models.TextChoices):
        PETITE = "PETITE", "Petite section"
        MOYENNE = "MOYENNE", "Moyenne section"
        GRANDE = "GRANDE", "Grande section"
        AUTRE = "AUTRE", "Autre"

    name = models.CharField(max_length=100, verbose_name="Nom de la classe")
    level = models.CharField(
        max_length=20,
        choices=Level.choices,
        default=Level.PETITE
    )
    capacity = models.PositiveIntegerField(default=25)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="preschool_classes"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["level", "name"]
        verbose_name = "Classe"
        verbose_name_plural = "Classes"

    def __str__(self):
        return f"{self.name} ({self.get_level_display()})"


class Guardian(models.Model):
    first_name = models.CharField(max_length=100, verbose_name="Prénom")
    last_name = models.CharField(max_length=100, verbose_name="Nom")
    telephone = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    profession = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = "Parent ou tuteur"
        verbose_name_plural = "Parents et tuteurs"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Child(models.Model):

    class Gender(models.TextChoices):
        BOY = "BOY", "Garçon"
        GIRL = "GIRL", "Fille"

    matricule = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="Matricule"
    )
    first_name = models.CharField(max_length=100, verbose_name="Prénom")
    last_name = models.CharField(max_length=100, verbose_name="Nom")
    date_of_birth = models.DateField(verbose_name="Date de naissance")
    gender = models.CharField(
        max_length=10,
        choices=Gender.choices
    )
    address = models.TextField(blank=True)
    photo = models.ImageField(
        upload_to="preschool/children/",
        blank=True,
        null=True
    )
    guardians = models.ManyToManyField(
        Guardian,
        through="ChildGuardian",
        related_name="children"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = "Élève"
        verbose_name_plural = "Élèves"

    def clean(self):
        if self.date_of_birth > timezone.localdate():
            raise ValidationError(
                "La date de naissance ne peut pas être dans le futur."
            )

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.matricule})"


class ChildGuardian(models.Model):

    class Relationship(models.TextChoices):
        FATHER = "FATHER", "Père"
        MOTHER = "MOTHER", "Mère"
        LEGAL_GUARDIAN = "LEGAL_GUARDIAN", "Tuteur légal"
        OTHER = "OTHER", "Autre"

    child = models.ForeignKey(Child, on_delete=models.CASCADE)
    guardian = models.ForeignKey(Guardian, on_delete=models.CASCADE)
    relationship = models.CharField(
        max_length=20,
        choices=Relationship.choices
    )
    is_primary = models.BooleanField(default=False)
    can_pick_up = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["child", "guardian"],
                name="unique_child_guardian"
            )
        ]
        verbose_name = "Lien élève-parent"
        verbose_name_plural = "Liens élèves-parents"

    def __str__(self):
        return f"{self.guardian} - {self.child}"


class Enrollment(models.Model):
    child = models.ForeignKey(
        Child,
        on_delete=models.PROTECT,
        related_name="enrollments"
    )
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.PROTECT,
        related_name="enrollments"
    )
    school_year = models.ForeignKey(
        SchoolYear,
        on_delete=models.PROTECT,
        related_name="enrollments"
    )
    enrollment_date = models.DateField(default=timezone.localdate)
    registration_number = models.CharField(
        max_length=40,
        unique=True
    )
    registration_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    tuition_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["child", "school_year"],
                name="unique_child_school_year"
            )
        ]
        ordering = ["-enrollment_date"]
        verbose_name = "Inscription"
        verbose_name_plural = "Inscriptions"

    def clean(self):
        if self.registration_fee < 0 or self.tuition_fee < 0:
            raise ValidationError(
                "Les frais ne peuvent pas être négatifs."
            )

    def __str__(self):
        return (
            f"{self.child} - {self.classroom} "
            f"({self.school_year})"
        )


class Attendance(models.Model):

    class Status(models.TextChoices):
        PRESENT = "PRESENT", "Présent"
        ABSENT = "ABSENT", "Absent"
        LATE = "LATE", "En retard"
        JUSTIFIED = "JUSTIFIED", "Absence justifiée"

    class JustificationStatus(models.TextChoices):
        NONE = "NONE", "Aucune"
        SUBMITTED = "SUBMITTED", "À valider"
        APPROVED = "APPROVED", "Approuvée"
        REJECTED = "REJECTED", "Rejetée"

    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name="attendances"
    )
    date = models.DateField(default=timezone.localdate)
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PRESENT
    )
    arrival_time = models.TimeField(null=True, blank=True)
    departure_time = models.TimeField(null=True, blank=True)
    observation = models.TextField(blank=True)
    justification_message = models.TextField(blank=True)
    justification_status = models.CharField(
        max_length=15,
        choices=JustificationStatus.choices,
        default=JustificationStatus.NONE,
    )
    justification_response = models.TextField(blank=True)
    justification_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_student_attendance_justifications",
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="preschool_attendances"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "date"],
                name="unique_enrollment_attendance_date"
            )
        ]
        ordering = ["-date"]
        verbose_name = "Présence"
        verbose_name_plural = "Présences"

    def __str__(self):
        return f"{self.enrollment.child} - {self.date}"


class TeacherAttendance(models.Model):

    class Status(models.TextChoices):
        PRESENT = "PRESENT", "Présent"
        ABSENT = "ABSENT", "Absent"
        LATE = "LATE", "En retard"

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="preschool_teacher_attendances",
    )
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.PROTECT,
        related_name="teacher_attendances",
    )
    date = models.DateField(default=timezone.localdate)
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PRESENT,
    )
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    note = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_preschool_teacher_attendances",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["teacher", "classroom", "date"],
                name="unique_teacher_classroom_attendance_date",
            )
        ]
        ordering = ["-date", "teacher__last_name"]
        verbose_name = "Présence enseignant"
        verbose_name_plural = "Présences enseignants"


class TeacherAbsenceRequest(models.Model):

    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED", "À traiter"
        APPROVED = "APPROVED", "Approuvée"
        REJECTED = "REJECTED", "Rejetée"

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="preschool_absence_requests",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    justification = models.TextField(blank=True)
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.SUBMITTED,
    )
    manager_message = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_preschool_absence_requests",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Demande d'absence enseignant"
        verbose_name_plural = "Demandes d'absence enseignants"


class ClassSession(models.Model):
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.PROTECT,
        related_name="sessions",
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="preschool_sessions",
    )
    title = models.CharField(max_length=150)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_preschool_sessions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["starts_at"]
        verbose_name = "Séance de cours"
        verbose_name_plural = "Séances de cours"


class CourseSupport(models.Model):
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        related_name="course_supports",
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="preschool_course_supports",
    )
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    resource_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Support de cours"
        verbose_name_plural = "Supports de cours"


class StudentAssessment(models.Model):

    class LearningArea(models.TextChoices):
        LANGUAGE = "LANGUAGE", "Langage"
        NUMERACY = "NUMERACY", "Découverte des nombres"
        MOTOR = "MOTOR", "Motricité"
        SOCIAL = "SOCIAL", "Vie sociale"
        CREATIVITY = "CREATIVITY", "Créativité"
        AUTONOMY = "AUTONOMY", "Autonomie"

    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name="assessments",
    )
    date = models.DateField(default=timezone.localdate)
    learning_area = models.CharField(
        max_length=20,
        choices=LearningArea.choices,
    )
    score = models.PositiveSmallIntegerField()
    observation = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="preschool_assessments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "enrollment__child__last_name"]
        verbose_name = "Évaluation de l'élève"
        verbose_name_plural = "Évaluations des élèves"

    def clean(self):
        if self.score < 1 or self.score > 5:
            raise ValidationError(
                "Le niveau d'acquisition doit être compris entre 1 et 5."
            )
