import uuid

from django.contrib.auth.models import User
from django.db import models

from hagrid.products.models import Variation


class Reservation(models.Model):
    STATE_UNAPPROVED = 'unapproved'
    STATE_EDITABLE = 'editable'
    STATE_SUBMITTED = 'submitted'
    STATE_PACKED = 'packed'
    STATE_READY = 'ready for pickup'
    STATE_PICKED_UP = 'picked up'
    STATE_CANCELLED = 'canceled'
    STATES = [
            (STATE_UNAPPROVED, 'unapproved'),
            (STATE_EDITABLE, 'editable'),
            (STATE_SUBMITTED, 'submitted'),
            (STATE_PACKED, 'packed'),
            (STATE_READY, 'ready to be picked up'),
            (STATE_PICKED_UP, 'picked up'),
            (STATE_CANCELLED, 'cancelled'),
    ]

    PACKING_MODE_AGGREGATED = 'aggregated'
    PACKING_MODE_SEPERATED_PARTS = 'seperated parts'
    PACKING_MODES = [
            (PACKING_MODE_AGGREGATED, "Don't seperate reservation parts"),
            (PACKING_MODE_SEPERATED_PARTS, "Pack every reservation part individually")
    ]

    team_name = models.CharField(max_length=30)
    contact_name = models.CharField(max_length=30)
    contact_mail = models.EmailField(blank=True)
    contact_dect = models.CharField(max_length=10, blank=True)
    secret = models.CharField(max_length=16, unique=True)
    action_secret = models.UUIDField(default=uuid.uuid4)
    state = models.CharField(max_length=20, choices=STATES, default=STATE_UNAPPROVED)
    comment = models.TextField(default="", blank=True)
    packing_mode = models.CharField(max_length=20, choices=PACKING_MODES, default=PACKING_MODE_AGGREGATED)

    def __str__(self):
        return "Reservation for {} by {}".format(self.team_name, self.contact_name)

    @property
    def price(self):
        return sum(part.price for part in self.parts.all())


class ReservationEvent(models.Model):
    old_state = models.CharField(max_length=20, choices=Reservation.STATES)
    new_state = models.CharField(max_length=20, choices=Reservation.STATES)
    datetime = models.DateTimeField(auto_now=True)
    reservation = models.ForeignKey(Reservation, related_name='events', on_delete=models.CASCADE)


class ReservationPart(models.Model):
    title = models.CharField(max_length=100)
    reservation = models.ForeignKey(Reservation, related_name='parts', on_delete=models.CASCADE)

    def __str__(self):
        return "Part of {} titled {}".format(str(self.reservation), self.title)

    @property
    def price(self):
        return sum(position.price for position in self.positions.all())


class ReservationPosition(models.Model):
    variation = models.ForeignKey(Variation, related_name='reservation_positions', on_delete=models.CASCADE)
    part = models.ForeignKey(ReservationPart, related_name='positions', on_delete=models.CASCADE)
    amount = models.PositiveSmallIntegerField(default=0)

    @property
    def price(self):
        return self.variation.product.price * self.amount
