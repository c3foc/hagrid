from django.contrib import admin

from .models import StaticPage, PageImage

admin.site.register(StaticPage)
admin.site.register(PageImage)
