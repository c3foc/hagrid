import random

from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from hagrid.operations.models import OpenStatus
from hagrid.gallery.models import GalleryImage

from ..models import (
    Product,
    ProductGroup,
    Size,
    SizeGroup,
    StoreSettings,
    Variation,
)
from ..tables import SizeTable


@cache_page(10)
@csrf_exempt
@require_GET
def dashboard(request):
    product_groups = ProductGroup.objects.filter(display_in_dashboard=True)
    all_products = Product.objects.all()
    all_variations = Variation.objects.all()
    all_sizegroups = SizeGroup.objects.all()
    all_sizes = Size.objects.all()
    bool(all_products)
    bool(all_variations)
    bool(all_sizegroups)
    bool(all_sizes)

    def _transform_sizegroup(sizegroup, product_variations):
        variations = (
            product_variations.filter(size__group=sizegroup)
            .order_by("size__position")
            .distinct()
        )

        return {
            "sizegroup": sizegroup,
            "variations": variations,
        }

    def _transform_product(product):
        variations = all_variations.filter(product=product)
        sizegroups = all_sizegroups.filter(
            sizes__variations__product=product
        ).distinct()
        images = list(GalleryImage.objects.filter(product=product))
        return {
            "product": product,
            "sizegroups": [
                _transform_sizegroup(sizegroup, variations) for sizegroup in sizegroups
            ],
            "image": random.choice(images) if images else None,
            "image_count_more": len(images) - 1,
        }

    def _transform_product_group(product_group):
        products = all_products.filter(product_group=product_group)

        return {
            "product_group": product_group,
            "products": list(_transform_product(p) for p in products),
        }

    product_availabilities = list(_transform_product_group(pg) for pg in product_groups)

    dashboard_text: str | None = StoreSettings.objects.first().dashboard_text
    if dashboard_text and "%open_status%" in dashboard_text:
        open_status = render_to_string(
            "open_status.html", {"open_status": OpenStatus.get_status()}
        )
        dashboard_text = dashboard_text.replace("%open_status%", open_status)

    context = {
        "products": Product.objects.all(),
        "sizes": Size.objects.all(),
        "sizegroups": SizeGroup.objects.all(),
        "variations": Variation.objects.all(),
        "product_availabilities": product_availabilities,
        "dashboard_text": dashboard_text,
    }

    return render(request, "dashboard.html", context)


@cache_page(10)
@csrf_exempt
@require_GET
def dashboard_table(request):
    def render_variation(variation):
        if variation.availability == Variation.STATE_MANY_AVAILABLE:
            return '<div class="text-center"><span class="badge bg-success">&#10003;</span></div>'
        if variation.availability == Variation.STATE_FEW_AVAILABLE:
            return '<div class="text-center"><span class="badge bg-warning">&#9888;</span></div>'
        if variation.availability == Variation.STATE_SOLD_OUT:
            return '<div class="text-center"><span class="badge bg-danger">&#10007;</span></div>'

    context = {
        # TODO: check if we all this content
        "products": Product.objects.all(),
        "sizes": Size.objects.all(),
        "sizegroups": SizeGroup.objects.all(),
        "variations": Variation.objects.all(),
        "availability_tables": [
            SizeTable(sg, render_variation=render_variation)
            for sg in SizeGroup.objects.all()
        ],
    }

    return render(request, "dashboard_table.html", context)
