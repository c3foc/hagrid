
from django.contrib import admin
from django.urls import include, path
from django.views.decorators.cache import cache_page

from . import views

urlpatterns = [
    path('', cache_page(10)(views.GalleryView.as_view()), name='gallery'),
]
