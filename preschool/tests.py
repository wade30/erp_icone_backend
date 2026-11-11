from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from finance.models import ExpenseRequest

from .models import (
    Attendance,
    Child,
    ChildGuardian,
    Classroom,
    Enrollment,
    Guardian,
    SchoolYear,
    TeacherAbsenceRequest,
)

User = get_user_model()


class PreschoolAccessTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher-a",
            password="test-password",
            role="STAFF",
            service="PRESCHOOL",
        )
        self.other_teacher = User.objects.create_user(
            username="teacher-b",
            password="test-password",
            role="STAFF",
            service="PRESCHOOL",
        )
        self.manager = User.objects.create_user(
            username="preschool-manager",
            password="test-password",
            role="SERVICE_MANAGER",
            service="PRESCHOOL",
        )
        self.classroom = Classroom.objects.create(
            name="Petite section A",
            teacher=self.teacher,
        )
        self.other_classroom = Classroom.objects.create(
            name="Moyenne section B",
            teacher=self.other_teacher,
        )
        self.guardian = Guardian.objects.create(
            first_name="Awa",
            last_name="Fall",
            telephone="770000000",
        )
        self.child = Child.objects.create(
            matricule="PRE-001",
            first_name="Moussa",
            last_name="Fall",
            date_of_birth=date(2021, 1, 1),
            gender=Child.Gender.BOY,
        )
        self.other_child = Child.objects.create(
            matricule="PRE-002",
            first_name="Aminata",
            last_name="Sow",
            date_of_birth=date(2021, 2, 1),
            gender=Child.Gender.GIRL,
        )
        school_year = SchoolYear.objects.create(
            name="2026-2027",
            start_date=date(2026, 9, 1),
            end_date=date(2027, 7, 1),
            is_active=True,
        )
        self.enrollment = Enrollment.objects.create(
            child=self.child,
            classroom=self.classroom,
            school_year=school_year,
            registration_number="REG-001",
        )
        Enrollment.objects.create(
            child=self.other_child,
            classroom=self.other_classroom,
            school_year=school_year,
            registration_number="REG-002",
        )
        ChildGuardian.objects.create(
            child=self.child,
            guardian=self.guardian,
            relationship=ChildGuardian.Relationship.MOTHER,
        )
        self.client = APIClient()

    def test_staff_reads_only_assigned_class_roster(self):
        self.client.force_authenticate(self.teacher)

        children = self.client.get("/api/preschool/children/")
        guardians = self.client.get("/api/preschool/guardians/")
        classrooms = self.client.get("/api/preschool/classrooms/")

        self.assertEqual(children.status_code, 200)
        self.assertEqual(
            [row["matricule"] for row in children.data["results"]],
            ["PRE-001"],
        )
        self.assertEqual(guardians.status_code, 200)
        self.assertEqual(
            [row["telephone"] for row in guardians.data["results"]],
            ["770000000"],
        )
        self.assertEqual(
            [row["name"] for row in classrooms.data["results"]],
            ["Petite section A"],
        )

    def test_staff_cannot_change_roster_but_can_request_absence(self):
        self.client.force_authenticate(self.teacher)

        denied = self.client.post(
            "/api/preschool/children/",
            {
                "matricule": "PRE-003",
                "first_name": "Ali",
                "last_name": "Diop",
                "date_of_birth": "2021-03-01",
                "gender": "BOY",
            },
        )
        absence = self.client.post(
            "/api/preschool/teacher-absence-requests/",
            {
                "start_date": "2026-11-10",
                "end_date": "2026-11-11",
                "reason": "Rendez-vous médical",
                "justification": "Certificat à fournir.",
            },
        )

        self.assertEqual(denied.status_code, 403)
        self.assertEqual(absence.status_code, 201)
        self.assertEqual(absence.data["teacher"], self.teacher.id)
        self.assertEqual(absence.data["status"], "SUBMITTED")

    def test_manager_can_approve_absence_with_feedback(self):
        absence = TeacherAbsenceRequest.objects.create(
            teacher=self.teacher,
            start_date=date(2026, 11, 10),
            end_date=date(2026, 11, 11),
            reason="Rendez-vous médical",
        )
        self.client.force_authenticate(self.manager)

        response = self.client.post(
            f"/api/preschool/teacher-absence-requests/{absence.id}/approve/",
            {
                "decision": "APPROVED",
                "manager_message": "Absence approuvée.",
            },
        )

        self.assertEqual(response.status_code, 200)
        absence.refresh_from_db()
        self.assertEqual(absence.status, TeacherAbsenceRequest.Status.APPROVED)
        self.assertEqual(absence.manager_message, "Absence approuvée.")
        self.assertEqual(absence.reviewed_by_id, self.manager.id)

    def test_manager_can_access_complete_preschool_roster(self):
        self.client.force_authenticate(self.manager)

        children = self.client.get("/api/preschool/children/")
        self.assertEqual(children.status_code, 200)
        self.assertEqual(len(children.data["results"]), 2)

    def test_teacher_submits_student_justification_for_manager_review(self):
        attendance = Attendance.objects.create(
            enrollment=self.enrollment,
            date=date(2026, 11, 9),
            status=Attendance.Status.ABSENT,
        )
        self.client.force_authenticate(self.teacher)
        submitted = self.client.post(
            f"/api/preschool/attendances/{attendance.id}/justify/",
            {"justification_message": "Le parent a prévenu l'enseignant."},
        )
        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(
            submitted.data["justification_status"],
            Attendance.JustificationStatus.SUBMITTED,
        )

        self.client.force_authenticate(self.manager)
        reviewed = self.client.post(
            f"/api/preschool/attendances/{attendance.id}/review-justification/",
            {
                "decision": "APPROVED",
                "manager_message": "Justificatif accepté.",
            },
        )
        self.assertEqual(reviewed.status_code, 200)
        attendance.refresh_from_db()
        self.assertEqual(attendance.status, Attendance.Status.JUSTIFIED)
        self.assertEqual(
            attendance.justification_status,
            Attendance.JustificationStatus.APPROVED,
        )

    def test_staff_cannot_record_attendance_for_another_class(self):
        self.client.force_authenticate(self.teacher)

        response = self.client.post(
            "/api/preschool/attendances/",
            {
                "enrollment": self.enrollment.id,
                "date": "2026-11-09",
                "status": "PRESENT",
            },
        )
        self.assertEqual(response.status_code, 201)

        unapproved_justification = self.client.post(
            "/api/preschool/attendances/",
            {
                "enrollment": self.enrollment.id,
                "date": "2026-11-10",
                "status": "JUSTIFIED",
            },
        )
        self.assertEqual(unapproved_justification.status_code, 403)

        foreign_enrollment = Enrollment.objects.get(
            classroom=self.other_classroom
        )
        denied = self.client.post(
            "/api/preschool/attendances/",
            {
                "enrollment": foreign_enrollment.id,
                "date": "2026-11-09",
                "status": "PRESENT",
            },
        )
        self.assertEqual(denied.status_code, 403)

    def test_staff_can_only_read_expense_requests_not_finance_operations(self):
        self.client.force_authenticate(self.teacher)

        requests = self.client.get("/api/finance/expenses/")
        receipts = self.client.get("/api/finance/receipts/")
        cash_expenses = self.client.get("/api/finance/cash-expenses/")

        self.assertEqual(requests.status_code, 200)
        self.assertEqual(receipts.status_code, 403)
        self.assertEqual(cash_expenses.status_code, 403)

    def test_user_can_update_personal_profile_without_changing_role(self):
        self.client.force_authenticate(self.teacher)

        updated = self.client.patch(
            "/api/auth/me/",
            {
                "first_name": "Aminata",
                "telephone": "771234567",
            },
            format="json",
        )
        forbidden = self.client.patch(
            "/api/auth/me/",
            {"role": "PDG"},
            format="json",
        )

        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["telephone"], "771234567")
        self.assertEqual(forbidden.status_code, 400)
        self.teacher.refresh_from_db()
        self.assertEqual(self.teacher.role, "STAFF")

    def test_service_manager_can_approve_own_service_expense_request(self):
        expense_request = ExpenseRequest.objects.create(
            date=date(2026, 11, 9),
            service="PRESCHOOL",
            category="Fournitures",
            description="Matériel pédagogique",
            amount="25000",
            requested_by=self.teacher,
            status=ExpenseRequest.Status.SUBMITTED,
        )
        self.client.force_authenticate(self.manager)

        response = self.client.post(
            f"/api/finance/expenses/{expense_request.id}/approve/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        expense_request.refresh_from_db()
        self.assertEqual(
            expense_request.status,
            ExpenseRequest.Status.APPROVED,
        )
        self.assertEqual(expense_request.approved_by_id, self.manager.id)
