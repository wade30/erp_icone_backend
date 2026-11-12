from rest_framework.routers import DefaultRouter

from .views import CourseViewSet, LearnerViewSet, EnrollmentViewSet

router = DefaultRouter()

router.register("courses", CourseViewSet)
router.register("learners", LearnerViewSet)
router.register("enrollments", EnrollmentViewSet)

urlpatterns = router.urls