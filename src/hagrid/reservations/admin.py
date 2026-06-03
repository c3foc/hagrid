from django.contrib import admin

from hagrid.reservations.models import *

admin.site.register(ReservationPart)
admin.site.register(ReservationPosition)
admin.site.register(ReservationEvent)


@admin.register(Reservation)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["team_name", "event", "state"]
    list_editable = ["event"]
    list_filter = ["event", "state"]
