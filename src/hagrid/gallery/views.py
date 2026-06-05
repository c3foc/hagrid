from django.shortcuts import render
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt

from .models import GalleryImage


@csrf_exempt
@cache_page(10)
def gallery_view(request, product_id=None):
    if product_id is not None:
        images = GalleryImage.objects.filter(design_variation__product__id=product_id)
    else:
        images = GalleryImage.objects.all()

    images = images.order_by(
        "-design_variation__design__event__day_1",
        "design_variation__product__category__position",
        "design_variation__product__position",
        "design_variation__design__position",
    )

    return render(
        request,
        "gallery.html",
        {
            "gallery_images": images,
        },
    )
