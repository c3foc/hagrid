
from django.contrib import admin
from django.urls import include, path

from .views import VariationConfigView, VariationChangeAvailabilityView, VariationAvailabilityEventListView, ProductConfigView

urlpatterns = [
    path('', VariationChangeAvailabilityView.as_view(), name='availabilityconfig'),
    path('variations/', VariationConfigView.as_view(), name='variationconfig'),
    path('history/', VariationAvailabilityEventListView.as_view(), name='variationavailabilityeventlist'),
    path('productsandsizes/', ProductConfigView.as_view(), name='productconfig'),
]
