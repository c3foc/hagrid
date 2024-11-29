
from django.contrib import admin
from django.urls import include, path

from .views import VariationConfigView, VariationChangeAvailabilityView, VariationAvailabilityEventListView, VariationCountView, VariationCountSuccessView

urlpatterns = [
    path('', VariationChangeAvailabilityView.as_view(), name='availabilityconfig'),
    path('variations/', VariationConfigView.as_view(), name='productconfig'),
    path('history/', VariationAvailabilityEventListView.as_view(), name='variationavailabilityeventlist'),
    path('count/success', VariationCountSuccessView.as_view(), name='variation_count_success'),
    path('count/<slug:code>/', VariationCountView.as_view(), name='variationcount'),
]
