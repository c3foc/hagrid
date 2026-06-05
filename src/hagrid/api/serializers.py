from rest_framework import serializers

from hagrid.products.models import Product, Size, SizeScale, SizeVariation


class ProductAPISerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"


class SizeScaleAPISerializer(serializers.ModelSerializer):
    class Meta:
        model = SizeScale
        fields = "__all__"


class SizeAPISerializer(serializers.ModelSerializer):
    scale = SizeScaleAPISerializer()

    class Meta:
        model = Size
        fields = "__all__"


class SizeVariationAPISerializer(serializers.ModelSerializer):
    size = SizeAPISerializer()
    product = ProductAPISerializer()

    class Meta:
        model = SizeVariation
        fields = "__all__"
