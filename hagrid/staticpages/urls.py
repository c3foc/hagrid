from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from .views import StaticPageView

urlpatterns = [
    path('<slug:page_slug>/', csrf_exempt()(StaticPageView.as_view()), name='staticpages'),
]
