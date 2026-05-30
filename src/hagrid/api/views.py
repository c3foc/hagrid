from rest_framework import generics, viewsets

from hagrid.api.serializers import (
    ProductAPISerializer,
    SizeAPISerializer,
    SizeGroupAPISerializer,
    VariationAPISerializer,
)
from hagrid.products.models import Product, Size, SizeGroup, Variation


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductAPISerializer


class SizeViewSet(viewsets.ModelViewSet):
    queryset = Size.objects.all()
    serializer_class = SizeAPISerializer


class SizeGroupViewSet(viewsets.ModelViewSet):
    queryset = SizeGroup.objects.all()
    serializer_class = SizeGroupAPISerializer


class VariationProductDetail(generics.ListAPIView):
    serializer_class = VariationAPISerializer

    def get_queryset(self):
        queryset = Variation.objects.all()
        product_id = self.request.query_params.get("product_id", None)
        if product_id is not None:
            queryset = queryset.filter(product__id=product_id)
        return queryset
