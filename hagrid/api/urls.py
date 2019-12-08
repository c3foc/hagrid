from django.conf.urls import url
from django.urls import path, include
from rest_framework import routers

from hagrid.api.views import VariationProductDetail, ProductViewSet, SizeViewSet, SizeGroupViewSet

router = routers.DefaultRouter()
router.register(r'product', ProductViewSet)
router.register(r'size', SizeViewSet)
router.register(r'sizegroup', SizeGroupViewSet)

urlpatterns = [
    path('v1/auth/', include('rest_framework.urls')),
    path('v1/', include(router.urls)),
    path('v1/variations', VariationProductDetail.as_view(), name='api_variations'),
]
