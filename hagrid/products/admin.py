
from django.contrib import admin

from .models import *

admin.site.register(StoreSettings)
admin.site.register(Product)
admin.site.register(Variation)
admin.site.register(SizeGroup)
admin.site.register(Size)
admin.site.register(AvailabilityEvent)
