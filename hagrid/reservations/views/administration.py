import datetime
from collections import namedtuple

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import View
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView
from django.utils.text import slugify

from hagrid.products.views import SizeTable

from ..models import Reservation, ReservationPart, ReservationPosition


class StateChangeForm(forms.Form):
    # Form rendering is hardcoded in ReservationAdministrationView.template_name
    reservation_id = forms.IntegerField()
    new_state = forms.ChoiceField(choices=Reservation.STATES)


class ReservationAdministrationView(LoginRequiredMixin, View):
    template_name = 'reservationadministration.html'
    StateButton = namedtuple('StateButton', ['state', 'label', 'active_classes', 'inactive_classes'])
    state_buttons = [
            StateButton(Reservation.STATE_UNAPPROVED, 'Unapproved', 'btn-secondary', 'btn-outline-secondary'),
            StateButton(Reservation.STATE_EDITABLE, 'Editable', 'btn-secondary', 'btn-outline-secondary'),
            StateButton(Reservation.STATE_SUBMITTED, 'Submitted', 'btn-secondary', 'btn-outline-secondary'),
            StateButton(Reservation.STATE_PACKED, 'Packed', 'btn-secondary', 'btn-outline-secondary'),
            StateButton(Reservation.STATE_READY, 'Ready', 'btn-secondary', 'btn-outline-secondary'),
            StateButton(Reservation.STATE_PICKED_UP, 'Picked up', 'btn-success', 'btn-outline-success'),
            StateButton(Reservation.STATE_CANCELLED, 'Cancelled', 'btn-danger', 'btn-outline-danger'),
    ]


    def post(self, request):
        form = StateChangeForm(request.POST)
        if form.is_valid():
            reservation = get_object_or_404(Reservation, id=form.cleaned_data['reservation_id'])
            reservation.state = form.cleaned_data['new_state']
            reservation.save()
        else:
            messages.add_message(request, messages.ERROR, 'This action could not be performed.')
        return redirect("reservationadministration")

    def get(self, request):
        return render(request, self.template_name, {
            'reservations': Reservation.objects.all(),
            'state_buttons': self.state_buttons,
        })


class ReservationPDFDownloadView(LoginRequiredMixin, View):
    def get(self, request, reservation_id):
        reservation = get_object_or_404(Reservation, id=reservation_id)
        filename = "c3foc-reservation_{number:02d}-{team_name}_{timestamp}.pdf".format(
                number=reservation.id,
                team_name=slugify(reservation.team_name),
                timestamp=datetime.datetime.now().strftime("%m-%d_%H%M%S")
        )

        data = b""

        response = HttpResponse(data, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        return response
