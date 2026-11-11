from rest_framework.routers import DefaultRouter

from .views import (
    EntrepreneurViewSet,
    ProjectViewSet,
    CoachingSessionViewSet,
)

router = DefaultRouter()

router.register("entrepreneurs", EntrepreneurViewSet)
router.register("projects", ProjectViewSet)
router.register("coaching-sessions", CoachingSessionViewSet)

urlpatterns = router.urls