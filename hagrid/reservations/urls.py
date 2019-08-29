
from django.contrib import admin
from django.urls import include, path

from .views import administration, teams

urlpatterns = [
    path('apply/', teams.ReservationApplicationView.as_view(), name='reservationapplication'),
    path('administration/', administration.ReservationAdministrationView.as_view(), name='reservationadministration'),
    path('administration/pdf/<int:reservation_id>/', administration.ReservationPDFDownloadView.as_view(), name='reservationpdf'),
    path('<slug:secret>/', teams.ReservationDetailView.as_view(), name='reservationdetail'),
    path('<slug:secret>/submit/', teams.ReservationSubmitView.as_view(), name='reservationsubmit'),
    path('<slug:secret>/part/create/', teams.ReservationPartCreateView.as_view(), name='reservationpartcreate'),
    path('<slug:secret>/part/<int:part_id>/', teams.ReservationPartDetailView.as_view(), name='reservationpartdetail'),
    path('<slug:secret>/part/<int:part_id>/delete/', teams.ReservationPartDeleteView.as_view(), name='reservationpartdelete'),
]
