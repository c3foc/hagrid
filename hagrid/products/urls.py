
from django.contrib import admin
from django.urls import include, path

from .views import ProductConfigView

urlpatterns = [
    path('', ProductConfigView.as_view(), name='productconfig'),
]
