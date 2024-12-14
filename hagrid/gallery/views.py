
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.cache import cache_page

from .models import GalleryImage

@cache_page(10)
def gallery_view(request, product_id=None):
    if isinstance(product_id, int):
        images = GalleryImage.objects.filter(variation__product__id=product_id)
    else:
        images = GalleryImage.objects.all()

    if not images:
        raise Http404()

    return render(request, "gallery.html", {
        'gallery_images': images,
    })
