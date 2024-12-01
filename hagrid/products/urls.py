from django.contrib import admin
from django.urls import include, path

from .views import (
    products_config_overview_view,
    variation_config_view,
    variation_availability_config_view,
    variation_availability_event_list_view,
    variation_count_overview_view,
    variation_count_view,
    variation_count_success_view,
)

urlpatterns = [
    path("", products_config_overview_view, name="products_config_overview"),
    path(
        "availability/",
        variation_availability_config_view,
        name="variation_availability_config",
    ),
    path(
        "availability/<int:product_id>/",
        variation_availability_config_view,
        name="variation_availability_config",
    ),
    path("variations/", variation_config_view, name="variation_config"),
    path("variations/<int:product_id>/", variation_config_view, name="variation_config"),
    path(
        "history/",
        variation_availability_event_list_view,
        name="variationavailabilityeventlist",
    ),
    path("count/", variation_count_overview_view, name="variation_count_overview"),
    path("count/success", variation_count_success_view, name="variation_count_success"),
    path("count/<slug:code>/", variation_count_view, name="variationcount"),
    path(
        "count/<slug:code>/<int:variation_id>",
        variation_count_view,
        name="variationcount",
    ),
]
