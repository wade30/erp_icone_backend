from rest_framework.routers import DefaultRouter

from .views import (
    BankAccountViewSet,
    CashExpenseViewSet,
    ReceiptViewSet,
    ExpenseRequestViewSet,
)

router = DefaultRouter()

router.register(
    "bank-accounts",
    BankAccountViewSet,
    basename="bank-account"
)

router.register(
    "cash-expenses",
    CashExpenseViewSet,
    basename="cash-expense"
)

router.register(
    "receipts",
    ReceiptViewSet,
    basename="receipt"
)

router.register(
    "expenses",
    ExpenseRequestViewSet,
    basename="expense-request"
)

urlpatterns = router.urls