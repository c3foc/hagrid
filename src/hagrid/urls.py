"""hagrid URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

import django_eventstream
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from hagrid.products.views.config import (
    htmx_update_variation_availability,
    operator_overview,
    size_variation_config,
    variation_availability_config,
    variation_availability_event_list,
    variation_count_config,
)
from hagrid.products.views.dashboard import dashboard, dashboard_table
from hagrid.products.views.stats import operator_stats
from hagrid.products.views.variation_count import (
    variation_count,
    variation_count_log,
    variation_count_overview,
    variation_count_success,
)


# auto-assign URL lookup name from function name
def p(pathname, fn):
    return path(pathname, fn, name=fn.__name__)


urlpatterns = [
    p("", dashboard),
    p("table", dashboard_table),
    p("operator/", operator_overview),
    p("operator/availability/", variation_availability_config),
    p("operator/availability/<int:product_id>/", variation_availability_config),
    p("operator/variations/", size_variation_config),
    p("operator/stats", operator_stats),
    p("operator/variations/<int:product_id>/", size_variation_config),
    p("operator/count/queue", variation_count_overview),
    p("operator/count/edit", variation_count_config),
    p("operator/count/log", variation_count_log),
    p("operator/count/<int:product_id>/", variation_count_config),
    p("history/", variation_availability_event_list),
    p("count/success", variation_count_success),
    p("count/<slug:code>/", variation_count),
    p("count/<slug:code>/<int:variation_id>", variation_count),
    path("admin/", admin.site.urls),
    path("reservations/", include("hagrid.reservations.urls")),
    path("gallery/", include("hagrid.gallery.urls")),
    path(
        "api/events/availability-display/",
        include(django_eventstream.urls),
        {"channels": ["availability-display"]},
    ),
    path(
        "api/events/availability-form/",
        include(django_eventstream.urls),
        {"channels": ["availability-form"]},
    ),
    path(
        "api/form/availability/<int:variation_id>/",
        htmx_update_variation_availability,
        name="htmx_update_variation_availability",
    ),
    path("api/", include("hagrid.api.urls")),
    path("pages/", include("hagrid.staticpages.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.ENABLE_DEBUG_TOOLBAR:
    import debug_toolbar

    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
