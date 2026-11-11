from rest_framework.routers import DefaultRouter

from .views import BudgetViewSet, BudgetLineViewSet

router = DefaultRouter()

router.register("budgets", BudgetViewSet)
router.register("budget-lines", BudgetLineViewSet)

urlpatterns = router.urls