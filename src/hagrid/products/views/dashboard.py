from typing import Any

from django.db.models import Max, Min
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from hagrid.operations.models import Event, OpenStatus
from hagrid.products.models import (
    DesignVariation,
    Price,
    Product,
    Size,
    SizeScale,
    SizeVariation,
    StoreSettings,
)


class ProductAvailabilityTable:
    """
    Data for a table to show with a unified size scale
    """

    def __init__(self, title, design_variations, product, price):
        self.title = title
        self.price = price
        self.design_variations = design_variations
        self.size_scale = product.size_scale
        self._sizes = list(self.size_scale.sizes.all())
        # todo images

    def iterate_size_label(self):
        for size in self._sizes:
            yield size.name

    def iterate_rows(self):
        """
        Yield tuples of product name, price, size availabilities
        """
        for design_variation in self.design_variations:
            size_mapping = {s: None for s in self._sizes}
            for size_variation in design_variation.size_variations.all():
                size_mapping[size_variation.size] = size_variation
            yield str(design_variation), [size_mapping[size] for size in self._sizes]


def get_current_open_status():
    return OpenStatus.objects.filter(datetime__lte=timezone.now()).order_by("-datetime").first()


@cache_page(10)
@csrf_exempt
@require_GET
def dashboard(request):
    open_status = get_current_open_status()
    sections = []

    if open_status is not None:
        current_event = open_status.event
        # ////
        tables = built_product_tables(current_event, [current_event])
        sections.append({"title": current_event.name, "tables": tables, "description": ""})
        if (other_events := open_status.selling_items_from.exclude(id=current_event.id)) and (
            other_event_tables := built_product_tables(current_event, other_events)
        ):
            sections.append({
                "title": "Previous Events",
                "tables": other_event_tables,
                "description": "",
            })

    dashboard_text: str | None = StoreSettings.objects.first().dashboard_text
    if dashboard_text and "%open_status%" in dashboard_text:
        open_status = render_to_string("open_status.html", {"open_status": OpenStatus.get_status()})
        dashboard_text = dashboard_text.replace("%open_status%", open_status)

    context = {
        "sections": sections,
        "dashboard_text": dashboard_text,
    }

    return render(request, "dashboard/dashboard.html", context)


def built_product_tables(current_event: Event, events: list[Any]) -> list[Any]:
    tables = []
    for product in Product.objects.all():
        design_variations = (
            DesignVariation.objects
            .filter(
                product=product,
                design__event__in=events,
            )
            .select_related("product__size_scale", "design__event")
            .prefetch_related(
                "size_variations__size",
            )
            .order_by("product__position")
        )
        if not design_variations:
            continue
        price = Price.objects.filter(
            valid_at=current_event,
            valid_for_products_from_event__in=events,
            product=product,
        ).aggregate(
            min_price=Min("amount"),
            max_price=Max("amount"),
        )
        tables.append(
            ProductAvailabilityTable(
                title=product.name,
                product=product,
                price=price,
                design_variations=design_variations,
            )
        )
    return tables


@cache_page(10)
@csrf_exempt
@require_GET
def dashboard_table(request):
    def render_variation(variation):
        if variation.availability == SizeVariation.STATE_MANY_AVAILABLE:
            return '<div class="text-center"><span class="badge bg-success">&#10003;</span></div>'
        if variation.availability == SizeVariation.STATE_FEW_AVAILABLE:
            return '<div class="text-center"><span class="badge bg-warning">&#9888;</span></div>'
        if variation.availability == SizeVariation.STATE_SOLD_OUT:
            return '<div class="text-center"><span class="badge bg-danger">&#10007;</span></div>'

    context = {
        # TODO: check if we all this content
        "products": Product.objects.all(),
        "sizes": Size.objects.all(),
        "SizeScales": SizeScale.objects.all(),
        "variations": SizeVariation.objects.all(),
        "availability_tables": [],
    }
    # TODO what is this view and how do we use it?
    return render(request, "dashboard_table.html", context)
