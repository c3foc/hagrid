from django.shortcuts import get_object_or_404
from django.views.generic.base import TemplateView

from .models import StaticPage

class StaticPageView(TemplateView):
    template_name = 'static_page_template.html'

    def get_context_data(self, **kwargs):
        return super().get_context_data(static_page=get_object_or_404(StaticPage, slug=self.kwargs['page_slug']),**kwargs)

