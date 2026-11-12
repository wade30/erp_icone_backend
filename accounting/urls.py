from rest_framework.routers import DefaultRouter

from .views import (
    AccountViewSet,
    JournalViewSet,
    AccountingEntryViewSet,
    EntryLineViewSet,
)

router = DefaultRouter()

router.register("accounts", AccountViewSet)
router.register("journals", JournalViewSet)
router.register("entries", AccountingEntryViewSet)
router.register("entry-lines", EntryLineViewSet)

urlpatterns = router.urls