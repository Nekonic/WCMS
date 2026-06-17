from rest_framework.routers import DefaultRouter

from .views import ClientViewSet

router = DefaultRouter()
router.register(r"pcs", ClientViewSet, basename="pc")

urlpatterns = router.urls
