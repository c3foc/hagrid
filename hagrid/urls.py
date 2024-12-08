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
from django.contrib import admin
from django.urls import include, path
from django.conf.urls.static import static
from django.conf import settings
from hagrid.products import views

# auto-assign URL lookup name from function name
def p(pathname, fn):
    return path(pathname, fn, name=fn.__name__)

urlpatterns = [
    p('', views.dashboard),
    p('table', views.dashboard_table),
    p('operator/', views.products_config_overview),
    p("operator/availability/", views.variation_availability_config),
    p("operator/availability/<int:product_id>/", views.variation_availability_config),
    p("operator/variations/", views.variation_config),
    p("operator/stats", views.operator_stats),
    p("operator/variations/<int:product_id>/", views.variation_config),
    p("operator/count/", views.variation_count_config),
    p("operator/count/<int:product_id>/", views.variation_count_config),
    p("history/", views.variation_availability_event_list),
    p("count/", views.variation_count_overview),
    p("count/success", views.variation_count_success),
    p("count/<slug:code>/", views.variation_count),
    p("count/<slug:code>/<int:variation_id>", views.variation_count),

    path('admin/', admin.site.urls),
    path('reservations/', include('hagrid.reservations.urls')),
    path('gallery/', include('hagrid.gallery.urls')),
    path('api/', include('hagrid.api.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
