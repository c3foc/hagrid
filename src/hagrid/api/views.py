from rest_framework import generics, viewsets

from hagrid.api.serializers import (
    ProductAPISerializer,
    SizeAPISerializer,
    SizeScaleAPISerializer,
    SizeVariationAPISerializer,
)
from hagrid.products.models import Product, Size, SizeScale, SizeVariation


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductAPISerializer


class SizeViewSet(viewsets.ModelViewSet):
    queryset = Size.objects.all()
    serializer_class = SizeAPISerializer


class SizeScaleViewSet(viewsets.ModelViewSet):
    queryset = SizeScale.objects.all()
    serializer_class = SizeScaleAPISerializer


class SizeVariationProductDetail(generics.ListAPIView):
    serializer_class = SizeVariationAPISerializer

    def get_queryset(self):
        queryset = SizeVariation.objects.all()
        product_id = self.request.query_params.get("product_id", None)
        if product_id is not None:
            queryset = queryset.filter(product__id=product_id)
        return queryset
