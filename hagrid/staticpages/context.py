from .models import StaticPage

def context_processor(request):
    return {
        "footerpages": StaticPage.objects.all().filter(show_in_footer=True),
        "headerpages": StaticPage.objects.all().filter(show_in_header=True),
    }
