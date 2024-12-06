from django.contrib import admin

from .models import OpenStatus

@admin.register(OpenStatus)
class SizeAdmin(admin.ModelAdmin):
    list_display = ["mode", "datetime", "comment", "public_info"]

