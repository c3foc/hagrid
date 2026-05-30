from django.contrib import admin

from .models import PageImage, StaticPage

admin.site.register(StaticPage)
admin.site.register(PageImage)
