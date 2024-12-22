
from django.urls import path

from . import views

urlpatterns = [
    path('', views.gallery_view, name='gallery'),
    path('<int:product_id>/', views.gallery_view, name='gallery'),
]
