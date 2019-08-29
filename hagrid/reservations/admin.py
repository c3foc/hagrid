
from django.contrib import admin

from hagrid.reservations.models import *

admin.site.register(Reservation)
admin.site.register(ReservationPart)
admin.site.register(ReservationPosition)
admin.site.register(ReservationEvent)
