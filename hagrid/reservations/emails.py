from django.core.mail import send_mail, mail_admins
from hagrid import settings
from django.urls import reverse
from hagrid.reservations.models import Reservation


def send_new_reservation_mail(reservation):
    if reservation.contact_mail:
        send_mail(
            "New Merchandise Reservation",
            """
Hello,

you have applied for a new reservation. You can access it using this link:

{}

Please wait until we approve your reservation.

c3foc
            """.format(
                settings.SITE_URL
                + reverse("reservationdetail", args=[reservation.secret])
            ),
            settings.EMAIL_FROM,
            [reservation.contact_mail],
            fail_silently=True,
        )
    mail_admins(
        "New reservation for {}".format(reservation.team_name),
        "Hagrid: {}".format(settings.SITE_URL),
        fail_silently=True,
    )


def send_reservation_state_changed_by_admin_mail(reservation, old_state, new_state):
    if old_state == new_state:
        return
    if new_state == Reservation.STATE_EDITABLE:
        send_reservation_editable_mail(reservation)
    elif new_state == Reservation.STATE_READY:
        send_reservation_ready_mail(reservation)


def send_reservation_editable_mail(reservation):
    if reservation.contact_mail:
        send_mail(
            "Merchandise Reservation editable",
            """
Hello,

your merchandise reservation can now be edited at

{}

c3foc
            """.format(
                settings.SITE_URL
                + reverse("reservationdetail", args=[reservation.secret])
            ),
            settings.EMAIL_FROM,
            [reservation.contact_mail],
            fail_silently=True,
        )


def send_reservation_submitted_mail(reservation):
    mail_admins(
        "Submitted reservation for {}".format(reservation.team_name),
        "Hagrid: {}".format(settings.SITE_URL),
        fail_silently=True,
    )


def send_reservation_ready_mail(reservation):
    if reservation.contact_mail:
        send_mail(
            "Merchandise Reservation ready",
            """
Hello,

your merchandise reservation can now be picked up.

{}

c3foc
            """.format(
                settings.SITE_URL
                + reverse("reservationdetail", args=[reservation.secret])
            ),
            settings.EMAIL_FROM,
            [reservation.contact_mail],
            fail_silently=True,
        )
