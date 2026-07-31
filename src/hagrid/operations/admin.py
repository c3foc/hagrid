from django.contrib import admin

from .models import Event, OpenStatus


@admin.register(OpenStatus)
class OpenStatusAdmin(admin.ModelAdmin):
    list_display = ["mode", "datetime", "event", "public_info"]
    list_editable = ["datetime"]
    list_filter = ["event"]


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ["name", "day_1", "last_day"]
