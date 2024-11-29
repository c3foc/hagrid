
from django.contrib import admin
from django.urls import include, path

from .views import ProductsConfigOverviewView, VariationConfigView, VariationAvailabilityConfigView, VariationAvailabilityEventListView, VariationCountView, VariationCountSuccessView

urlpatterns = [
    path('', ProductsConfigOverviewView.as_view(), name='products_config_overview'),
    path('availability/', VariationAvailabilityConfigView.as_view(), name='variation_availability_config'),
    path('availability/<int:product_id>/', VariationAvailabilityConfigView.as_view(), name='variation_availability_config'),
    path('variations/', VariationConfigView.as_view(), name='variation_config'),
    path('variations/<int:product_id>/', VariationConfigView.as_view(), name='variation_config'),
    path('history/', VariationAvailabilityEventListView.as_view(), name='variationavailabilityeventlist'),
    path('count/success', VariationCountSuccessView.as_view(), name='variation_count_success'),
    path('count/<slug:code>/', VariationCountView.as_view(), name='variationcount'),
]
