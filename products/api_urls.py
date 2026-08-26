from rest_framework.routers import DefaultRouter
from .api_views import ProductViewset

router = DefaultRouter()

router.register(
    'products',
    ProductViewset,
    basename='product',
)

urlpatterns = router.urls