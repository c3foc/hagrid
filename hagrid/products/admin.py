
from django.contrib import admin

from .models import *

admin.site.register(StoreSettings)
admin.site.register(Variation)
admin.site.register(SizeGroup)
admin.site.register(VariationAvailabilityEvent)
admin.site.register(ProductGroup)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'position', 'product_group']
    list_editable = ['price', 'position', 'product_group']
    list_filter=['product_group']

@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ['name', 'group']
    list_display_links = ['name']
    list_filter = ['group']


