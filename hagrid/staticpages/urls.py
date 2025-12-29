from django.urls import path

from .views import StaticPagesView

urlpatterns = [
    path('<slug:page_slug>/', StaticPagesView.as_view(), name='staticpages'),
]
