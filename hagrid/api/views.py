from django.http import HttpResponseBadRequest
from django.urls import reverse_lazy
from rest_framework import generics, viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView

from hagrid.api.serializers import (
    VariationAPISerializer,
    ProductAPISerializer,
    SizeAPISerializer,
    SizeGroupAPISerializer,
)
from hagrid.products.models import Variation, Product, Size, SizeGroup


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
