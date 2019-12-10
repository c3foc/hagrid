import datetime
from collections import namedtuple

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.text import slugify
from django.views import View
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView
from django.utils.text import slugify

from hagrid.products.views import SizeTable

from ..models import Reservation, ReservationPart, ReservationPosition
from ..export_pdf import generate_packing_pdf


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

        data = generate_packing_pdf([reservation], filename, username=request.user.username)

        response = HttpResponse(data, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        return response


class ReservationPackedActionForm(forms.Form):

    BEHAVIOUR_CHOICES = [('behaviour__set_packed', 'Only set reservation to packed'),
            ('behaviour__set_ready_for_pickup', 'Set reservation to packed and ready for pickup')]

    i_checked_my_action = forms.BooleanField()
    requested_behaviour = forms.ChoiceField(label="Desired Action: ",
            widget=forms.RadioSelect, choices=BEHAVIOUR_CHOICES,
            initial='behaviour__set_packed')


class ReservationPackedAction(LoginRequiredMixin, View):

    template_name = 'reservationactionpacked.html'


    def load_object_or_fail(self, secret, action_secret):
        reservation = get_object_or_404(Reservation, secret=secret)
        if action_secret != slugify(str(reservation.action_secret)):
            raise PermissionDenied("You don't have the permission to perform this action.")
        return reservation


    def get(self, request, secret, action_secret):
        reservation = self.load_object_or_fail(secret, action_secret)
        return render(request, self.template_name, {
                'reservation': reservation,
                'form': ReservationPackedActionForm(),
            })


    def post(self, request, secret, action_secret):
        f = ReservationPackedActionForm(request.POST)
        reservation = self.load_object_or_fail(secret, action_secret)
        if f.is_valid():
            if f.cleaned_data['i_checked_my_action']:
                # We need to imply this additional check just in case
                # someone manipulates the hypertext
                if f.cleaned_data['requested_behaviour'] == 'behaviour__set_packed':
                    reservation.state = Reservation.STATE_PACKED
                elif f.cleaned_data['requested_behaviour'] == 'behaviour__set_ready_for_pickup':
                    reservation.state = Reservation.STATE_READY
                reservation.save()
        return render(request, self.template_name, {
                'reservation': reservation,
                'form': f,
            })

