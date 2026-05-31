from django.urls import include, path
from rest_framework import routers

from hagrid.api.views import (
    ProductViewSet,
    SizeScaleViewSet,
    SizeVariationProductDetail,
    SizeViewSet,
)

router = routers.DefaultRouter()
router.register(r"product", ProductViewSet)
router.register(r"size", SizeViewSet)
router.register(r"sizescale", SizeScaleViewSet)

urlpatterns = [
    path("v1/auth/", include("rest_framework.urls")),
    path("v1/", include(router.urls)),
    path("v1/variations/", SizeVariationProductDetail.as_view(), name="api_variations"),
]
