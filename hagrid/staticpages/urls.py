from django.urls import path

from .views import StaticPageView

urlpatterns = [
    path('<slug:page_slug>/', StaticPageView.as_view(), name='staticpages'),
]
