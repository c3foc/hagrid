import asyncio
from typing import Any

from asgiref.sync import sync_to_async
from django.db.models import Max, Min
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from hagrid.gallery.models import GalleryImage
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


class DashboardTable:
    def __init__(self, title, design_variations, product, price):
        self.title = title
        self.price = price
        self.design_variations = design_variations
        self.size_scale = product.size_scale
        self._sizes = list(self.size_scale.sizes.all())
        self.image = None
        self.image_count_more = 0

    async def fetch_images(self):
        images = GalleryImage.objects.filter(design_variation__in=self.design_variations)
        self.image = await images.afirst()
        self.image_count_more = max(0, await images.acount() - 1)

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


def _open_status():
    return (
        OpenStatus.objects
        .filter(datetime__lte=timezone.now())
        .select_related("event")
        .order_by("-datetime")
    )


def get_current_open_status():
    return _open_status().first()


async def _get_status_context():
    now = timezone.now()

    prev_status, next_status = await asyncio.gather(
        OpenStatus.objects.filter(datetime__lt=now).order_by("-datetime").afirst(),
        OpenStatus.objects.filter(datetime__gte=now).order_by("datetime").afirst(),
    )
    is_open = prev_status.open if prev_status else False

    return {
        "open": is_open,
        "start": prev_status.datetime if prev_status else None,
        "stop": next_status.datetime if next_status else None,
        "closed_info": prev_status.public_info
        if not is_open
        else (next_status.public_info if next_status else None),
        "open_info": prev_status.public_info
        if is_open
        else (next_status.public_info if next_status else None),
    }


@cache_page(10)
@require_GET
async def dashboard(request):
    store_settings, open_status = await asyncio.gather(
        StoreSettings.objects.afirst(), _open_status().afirst()
    )

    dashboard_text = None
    if store_settings is not None and "%open_status%" in (
        dashboard_text := store_settings.dashboard_text
    ):
        status_text = render_to_string(
            "open_status.html", {"open_status": await _get_status_context()}
        )
        dashboard_text = dashboard_text.replace("%open_status%", status_text)

    sections = []
    if open_status is not None:
        current_event = open_status.event
        tables = await built_product_tables(current_event, [current_event])
        sections.append({"title": current_event.name, "tables": tables, "description": ""})
        other_events = [
            e
            async for e in open_status.selling_items_from.exclude(id=current_event.id).values_list(
                "id", flat=True
            )
        ]
        if other_events and (
            other_event_tables := await built_product_tables(current_event, other_events)
        ):
            sections.append({
                "title": "Previous Events",
                "tables": other_event_tables,
                "description": "",
            })

    context = {
        "sections": sections,
        "dashboard_text": dashboard_text,
    }

    return await sync_to_async(lambda: render(request, "dashboard/dashboard.html", context))()


async def built_product_tables(current_event: Event, events: list[Any]) -> list[Any]:
    async def _produce_table(product):
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
        if not [_ async for _ in design_variations]:
            return None
        price = await Price.objects.filter(
            valid_at=current_event,
            valid_for_products_from_event__in=events,
            product=product,
        ).aaggregate(
            min_price=Min("amount"),
            max_price=Max("amount"),
        )
        table = DashboardTable(
            title=product.name,
            product=product,
            price=price,
            design_variations=design_variations,
        )
        await table.fetch_images()
        return table

    # gather tables and filter out None
    return list(
        filter(
            bool,
            await asyncio.gather(*[
                _produce_table(p)
                async for p in Product.objects
                .select_related("size_scale")
                .prefetch_related("size_scale__sizes")
                .all()
            ]),
        )
    )


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
