from django.contrib import admin

from .models import StaticPage


@admin.register(StaticPage)
class PriceAdmin(admin.ModelAdmin):
    list_display = ["slug", "title", "show_in_footer", "show_in_header"]
    list_editable = ["show_in_footer", "show_in_header"]
    list_filter = []
