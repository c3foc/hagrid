
from .models import StoreSettings

def contextprocessor(request):
    return {'store_settings': StoreSettings.objects.first()}

