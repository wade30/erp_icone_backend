
from datetime import date

from django.db.models import Sum, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from .permissions import ERPModulePermission

from finance.models import CashExpense, Receipt, ExpenseRequest
from budgeting.models import BudgetLine

from incubator.models import CoachingSession, Entrepreneur, Project
from institute.models import Course, Enrollment, Learner
from marketing.models import Client, Contract, ServiceOrder
from orientation.models import Appointment, Beneficiary, OrientationRecord

from preschool.models import (
    Child,
    Classroom,
    Enrollment as PreschoolEnrollment,
    Attendance,
    Guardian,
)

from .models import User
from .serializers import UserSerializer, UserCreateSerializer, UserRegistrationSerializer
from rest_framework import generics
from rest_framework.permissions import AllowAny

# ============================================================
# 1. GESTION DES UTILISATEURS
# ============================================================

class UserRegistrationView(generics.CreateAPIView):

    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

class UserViewSet(viewsets.ModelViewSet):

    queryset = User.objects.all()

    permission_classes = [
        IsAuthenticated,
        ERPModulePermission,
    ]

    permission_module = "users"
    permission_shared_data = True

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer

        return UserSerializer


# ============================================================
# 2. TABLEAU DE BORD CENTRAL
# ============================================================

class DashboardView(APIView):

    permission_classes = [IsAuthenticated]

    SERVICES = (
        ("INSTITUTE", "Institut numérique"),
        ("INCUBATOR", "Incubateur"),
        ("MARKETING", "Agence marketing"),
        ("ORIENTATION", "Accueil et orientation"),
        ("PRESCHOOL", "Préscolaire"),
    )

    DASHBOARD_MODULES = {
        "INSTITUTE": "institute",
        "INCUBATOR": "incubator",
        "MARKETING": "marketing",
        "ORIENTATION": "orientation",
        "PRESCHOOL": "preschool",
    }

    ALL_DASHBOARDS = (
        "finance",
        "institute",
        "incubator",
        "marketing",
        "orientation",
        "preschool",
    )

    GLOBAL_ROLES = {
        "SECRETARY",
        "SECRETAIRE",
        "DIRECTOR",
        "PDG",
    }

    FINANCIAL_ROLES = {
        "FINANCE",
        "ACCOUNTANT",
        "SECRETARY",
        "SECRETAIRE",
        "DIRECTOR",
        "PDG",
    }

    # --------------------------------------------------------
    # IDENTIFICATION DU RÔLE
    # --------------------------------------------------------

    def get_role(self, user):
        return str(user.role).upper()

    # --------------------------------------------------------
    # DROITS D'AFFICHAGE DES DASHBOARDS
    # --------------------------------------------------------

    def get_dashboard_access(self, user):

        role = self.get_role(user)

        access = {
            "general": True,
            "finance": False,
            "institute": False,
            "incubator": False,
            "marketing": False,
            "orientation": False,
            "preschool": False,
        }

        # PDG, Directeur et Secrétaire générale
        if role in self.GLOBAL_ROLES:

            for dashboard in self.ALL_DASHBOARDS:
                access[dashboard] = True

            return access

        # Finance et comptabilité
        if role in {"FINANCE", "ACCOUNTANT"}:
            access["finance"] = True
            return access

        # Responsables et collaborateurs opérationnels
        service = getattr(user, "service", None)

        dashboard = self.DASHBOARD_MODULES.get(service)

        if dashboard:
            access[dashboard] = True

        return access

    # --------------------------------------------------------
    # ACTIVITÉS D'UN SERVICE
    # --------------------------------------------------------

    def get_service_activities(self, service):

        if service == "INSTITUTE":

            counts = {
                "courses": Course.objects.count(),
                "learners": Learner.objects.count(),
                "enrollments": Enrollment.objects.count(),
            }

        elif service == "INCUBATOR":

            counts = {
                "entrepreneurs": Entrepreneur.objects.count(),
                "projects": Project.objects.count(),
                "coaching_sessions": CoachingSession.objects.count(),
            }

        elif service == "MARKETING":

            counts = {
                "clients": Client.objects.count(),
                "contracts": Contract.objects.count(),
                "orders": ServiceOrder.objects.count(),
            }

        elif service == "ORIENTATION":

            counts = {
                "beneficiaries": Beneficiary.objects.count(),
                "appointments": Appointment.objects.count(),
                "orientation_records": OrientationRecord.objects.count(),
            }

        elif service == "PRESCHOOL":

            counts = {
                "children": Child.objects.count(),
                "classrooms": Classroom.objects.count(),
                "guardians": Guardian.objects.count(),
                "enrollments": PreschoolEnrollment.objects.count(),
                "attendances": Attendance.objects.count(),
            }

        else:
            counts = {}

        return counts

    # --------------------------------------------------------
    # INDICATEURS FINANCIERS PAR SERVICE
    # --------------------------------------------------------

    def get_financial_metrics(self, service, label):

        receipts = Receipt.objects.filter(
            service=service,
            status=Receipt.Status.COMPLETED,
        )

        expenses = CashExpense.objects.filter(
            service=service,
            status=CashExpense.Status.COMPLETED,
        )

        receipt_total = (
            receipts.aggregate(
                total=Sum("amount")
            )["total"] or 0
        )

        expense_total = (
            expenses.aggregate(
                total=Sum("amount")
            )["total"] or 0
        )

        return {
            "service": service,
            "label": label,
            "receipt_count": receipts.count(),
            "expense_count": expenses.count(),
            "receipt_total": receipt_total,
            "expense_total": expense_total,
        }

    # --------------------------------------------------------
    # INDICATEURS BUDGÉTAIRES PAR SERVICE
    # --------------------------------------------------------

    def get_budget_metrics(self, service, label):

        budget_lines = BudgetLine.objects.filter(
            budget__service=service,
            budget__status="APPROVED",
        )

        forecasts = budget_lines.aggregate(
            income_forecast=Sum(
                "revised_amount",
                filter=Q(nature="INCOME"),
            ),
            expense_forecast=Sum(
                "revised_amount",
                filter=Q(nature="EXPENSE"),
            ),
        )

        income_forecast = forecasts["income_forecast"] or 0
        expense_forecast = forecasts["expense_forecast"] or 0

        committed = ExpenseRequest.objects.filter(
            service=service,
            budget_line__budget__status="APPROVED",
            status__in=["APPROVED", "PAID"],
        ).aggregate(
            total=Sum("amount")
        )["total"] or 0

        paid = CashExpense.objects.filter(
            service=service,
            status=CashExpense.Status.COMPLETED,
            budget_line__budget__status="APPROVED",
        ).aggregate(
            total=Sum("amount")
        )["total"] or 0

        available = expense_forecast - committed

        execution_rate = (
            float(paid) / float(expense_forecast) * 100
            if expense_forecast
            else 0
        )

        return {
            "service": service,
            "label": label,
            "income_forecast": income_forecast,
            "expense_forecast": expense_forecast,
            "expense_committed": committed,
            "expense_paid": paid,
            "expense_available": available,
            "execution_rate": round(execution_rate, 2),
        }

    # --------------------------------------------------------
    # ÉVOLUTION MENSUELLE DES DÉPENSES
    # --------------------------------------------------------

    def get_expense_evolution(self, service_codes):

        if not service_codes:
            return []

        today = timezone.localdate()

        start_date = date(
            today.year - 1,
            today.month,
            1,
        )

        expenses = (
            CashExpense.objects.filter(
                service__in=service_codes,
                status=CashExpense.Status.COMPLETED,
                date__gte=start_date,
                date__lte=today,
            )
            .annotate(month=TruncMonth("date"))
            .values("month")
            .annotate(total=Sum("amount"))
            .order_by("month")
        )

        return [
            {
                "month": item["month"].strftime("%Y-%m"),
                "total": item["total"] or 0,
            }
            for item in expenses
        ]

    # ========================================================
    # 3. CONSTRUCTION DE LA RÉPONSE
    # ========================================================

    def get(self, request):

        user = request.user
        role = self.get_role(user)

        # ----------------------------------------------------
        # PERMISSIONS
        # ----------------------------------------------------

        dashboard_access = self.get_dashboard_access(user)

        is_global = role in self.GLOBAL_ROLES

        can_view_all_finances = role in self.FINANCIAL_ROLES

        # ----------------------------------------------------
        # SERVICES AUTORISÉS POUR LES ACTIVITÉS
        # ----------------------------------------------------

        if is_global:

            activity_services = self.SERVICES

        else:

            activity_services = tuple(
                item
                for item in self.SERVICES
                if item[0] == user.service
            )

        # ----------------------------------------------------
        # SERVICES AUTORISÉS POUR LES FINANCES
        # ----------------------------------------------------

        if can_view_all_finances:

            financial_services = self.SERVICES

        else:

            financial_services = tuple(
                item
                for item in self.SERVICES
                if item[0] == user.service
            )

        # ----------------------------------------------------
        # ACTIVITÉS OPÉRATIONNELLES
        # ----------------------------------------------------

        services = []

        for service, label in activity_services:

            counts = self.get_service_activities(service)

            services.append({
                "service": service,
                "label": label,
                **counts,
                "activity_count": sum(counts.values()),
            })

        total_activity = sum(
            item["activity_count"]
            for item in services
        )

        # ----------------------------------------------------
        # INDICATEURS FINANCIERS
        # ----------------------------------------------------

        financial_data = []

        for service, label in financial_services:

            financial_data.append(
                self.get_financial_metrics(service, label)
            )

        total_receipts = sum(
            item["receipt_total"]
            for item in financial_data
        )

        total_expenses = sum(
            item["expense_total"]
            for item in financial_data
        )

        financial_balance = (
            total_receipts - total_expenses
        )

        # ----------------------------------------------------
        # INDICATEURS BUDGÉTAIRES
        # ----------------------------------------------------

        budget_services = []

        for service, label in financial_services:

            budget_services.append(
                self.get_budget_metrics(service, label)
            )

        total_income_forecast = sum(
            item["income_forecast"]
            for item in budget_services
        )

        total_expense_forecast = sum(
            item["expense_forecast"]
            for item in budget_services
        )

        total_expense_committed = sum(
            item["expense_committed"]
            for item in budget_services
        )

        total_expense_paid = sum(
            item["expense_paid"]
            for item in budget_services
        )

        total_expense_available = sum(
            item["expense_available"]
            for item in budget_services
        )

        total_execution_rate = (
            total_expense_paid / total_expense_forecast * 100
            if total_expense_forecast
            else 0
        )

        # ----------------------------------------------------
        # ÉVOLUTION DES DÉPENSES
        # ----------------------------------------------------

        financial_service_codes = [
            service
            for service, label in financial_services
        ]

        expense_evolution = self.get_expense_evolution(
            financial_service_codes
        )

        # ----------------------------------------------------
        # RÉPONSE API
        # ----------------------------------------------------

        return Response({

            # Profil connecté
            "user": {
                "id": user.id,
                "username": user.username,
                "role": role,
                "service": user.service,
            },

            # Accès aux dashboards
            "dashboard_access": dashboard_access,

            # Permissions générales
            "permissions": {
                "can_view_all_activities": is_global,
                "can_view_all_finances": can_view_all_finances,
            },

            # Activités opérationnelles
            "services": services,
            "total_activity": total_activity,

            # Finances
            "financial_services": financial_data,
            "total_receipts": total_receipts,
            "total_expenses": total_expenses,
            "financial_balance": financial_balance,

            # Budgets
            "budget_services": budget_services,
            "total_income_forecast": total_income_forecast,
            "total_expense_forecast": total_expense_forecast,
            "total_expense_committed": total_expense_committed,
            "total_expense_paid": total_expense_paid,
            "total_expense_available": total_expense_available,
            "total_execution_rate": round(
                total_execution_rate,
                2,
            ),

            # Évolution mensuelle
            "expense_evolution": expense_evolution,
        })
