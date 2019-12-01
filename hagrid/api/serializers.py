from hagrid.products.models import Variation, Product, Size, SizeGroup
from rest_framework import serializers, viewsets


class ProductAPISerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'


class SizeGroupAPISerializer(serializers.ModelSerializer):
    class Meta:
        model = SizeGroup
        fields = '__all__'


class SizeAPISerializer(serializers.ModelSerializer):
    group = SizeGroupAPISerializer()
    class Meta:
        model = Size
        fields = '__all__'


class VariationAPISerializer(serializers.ModelSerializer):
    size = SizeAPISerializer()
    product = ProductAPISerializer()
    class Meta:
        model = Variation
        fields = '__all__'
