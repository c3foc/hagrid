from django import forms
from django.contrib import messages
from django.contrib.auth.views import login_required
from django.db.models import Max, Min
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods
from django.views.generic import FormView

from hagrid.operations.models import Event, OpenStatus
from hagrid.products.models import (
    AvailabilityEvent,
    CountEvent,
    DesignVariation,
    Price,
    Product,
    ProductCategory,
    SizeVariation,
)
from hagrid.products.tables import ProductTable
from hagrid.products.views.dashboard import get_current_open_status


class SizeVariationConfigForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["design_variation"].widget = forms.HiddenInput()
        self.fields["size"].widget = forms.HiddenInput()

    class Meta:
        model = SizeVariation
        fields = ["amount_initial", "amount_preordered", "design_variation", "size"]


@login_required()
@require_http_methods(["GET", "POST"])
def size_variation_config(request, product_id=None):
    products = list(
        Product.objects.all() if product_id is None else Product.objects.filter(id=product_id)
    )

    variation_forms = []

    def render_form(form, variation=None):
        return render_to_string(
            "operator/size_variation_config_box.html", context={"form": form}, request=request
        )

    def render_variation_form(size_variation):
        prefix = f"variation-{size_variation.design_variation_id}-{size_variation.size_id}"
        if request.POST:
            form = SizeVariationConfigForm(request.POST, prefix=prefix)
        else:
            form = SizeVariationConfigForm(prefix=prefix, instance=size_variation)
        variation_forms.append(form)
        return render_form(form, size_variation)

    def render_empty_form(design_variation, size):
        prefix = f"variation-{design_variation.id}-{size.id}"
        if request.POST:
            form = SizeVariationConfigForm(request.POST, prefix=prefix)
        else:
            form = SizeVariationConfigForm(
                prefix=prefix,
                initial={"design_variation": design_variation, "size": size},
            )
        variation_forms.append(form)
        return render_form(form)

    open_status = get_current_open_status()
    current_event = open_status.event if open_status else Event.objects.order_by("-day_1").first()
    tables = [
        table
        for event_groups, label in [
            ({current_event}, current_event.name),
            (set(Event.objects.all()) - {current_event}, "old"),
        ]
        for product in products
        if (
            table := ProductTable(
                title=f"{label} {product.name}",
                product=product,
                only_events_in=event_groups,
                render_variation=render_variation_form,
                render_empty=render_empty_form,
                show_empty_rows=True,
            )
        ).rows
    ]

    if request.POST and all(f.is_valid() for f in variation_forms):
        changed_count = 0
        created_count = 0
        deleted_count = 0

        for form in variation_forms:
            amount_initial = form.cleaned_data["amount_initial"]
            amount_preordered = form.cleaned_data["amount_preordered"]
            if amount_initial is not None:
                variation, created = SizeVariation.objects.get_or_create(
                    design_variation=form.cleaned_data["design_variation"],
                    size=form.cleaned_data["size"],
                    defaults={
                        "amount_initial": amount_initial,
                        "amount_preordered": amount_preordered,
                        "availability": SizeVariation.STATE_MANY_AVAILABLE,
                    },
                )
                if not created and variation.amount_initial != amount_initial:
                    changed_count += 1
                    variation.amount_initial = amount_initial
                    variation.save()
                elif created:
                    created_count += 1
            else:
                del_count, _ = SizeVariation.objects.filter(
                    design_variation=form.cleaned_data["design_variation"],
                    size=form.cleaned_data["size"],
                ).delete()
                deleted_count += del_count

        total_count = changed_count + created_count + deleted_count
        messages.add_message(
            request,
            messages.SUCCESS,
            f"Changed {total_count} variations (created {created_count}, modified {changed_count}, deleted {deleted_count})",
        )

        return redirect("operator_overview")

    return render(
        request,
        "operator/size_variation_config.html",
        {
            "products": products,
            "product_tables": tables,
        },
    )


class VariationsAvailabilityForm(forms.Form):
    def __init__(self, variations, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for variation in variations:
            key = f"variation_{variation.pk}"
            self.fields[key] = forms.ChoiceField(
                choices=SizeVariation.AVAILABILITY_STATES,
                initial=variation.availability,
                widget=forms.RadioSelect(
                    choices=SizeVariation.AVAILABILITY_STATES,
                ),
            )

    def field_for_rendering_by_variation(self, variation):
        key = f"variation_{variation.pk}"
        return self[key]


@login_required()
@require_http_methods(["GET", "POST"])
def variation_availability_config(request, product_id=None):
    products = Product.objects.all()
    if product_id is not None:
        products = products.filter(id=product_id)
    variations = list(SizeVariation.objects.filter(design_variation__product__in=products).all())

    form = VariationsAvailabilityForm(variations, request.POST or None)

    def render_variation_form(variation):
        field = form.field_for_rendering_by_variation(variation)
        return render_to_string(
            "operator/variation_availability_box.html",
            context={"field": field, "variation": variation},
            request=request,
        )

    def render_empty_form(product, size):
        return ""

    open_status = get_current_open_status()
    current_event = open_status.event if open_status else Event.objects.order_by("-day_1").first()
    tables = [
        table
        for event_groups, label in [
            ({current_event}, current_event.name),
            (set(Event.objects.all()) - {current_event}, "old"),
        ]
        for product in products
        if (
            table := ProductTable(
                title=f"{label} {product.name}",
                product=product,
                only_events_in=event_groups,
                render_variation=render_variation_form,
                render_empty=render_empty_form,
                show_empty_rows=False,
                table_class="availabilities-table",
            )
        ).rows
    ]

    if request.POST and form.is_valid():
        changed_count = 0
        for key, value in form.cleaned_data.items():
            variation_id = int(key.rsplit("_", 1)[-1])
            variation = get_object_or_404(SizeVariation, id=variation_id)
            if variation.availability != value:
                variation.availability = value
                variation.save()
                changed_count += 1
        messages.add_message(
            request,
            messages.SUCCESS,
            f"Changed {changed_count} availabilities",
        )
        return (
            redirect("variation_availability_config", product_id)
            if product_id
            else redirect("variation_availability_config")
        )

    context = {"tables": tables}
    return render(request, "operator/variation_availability_config.html", context)


@login_required()
@require_http_methods(["POST"])
def htmx_update_variation_availability(request, variation_id):
    variation = get_object_or_404(SizeVariation, pk=variation_id)
    form = VariationsAvailabilityForm(variations=[variation], data=request.POST)
    if form.is_valid():
        value = form.cleaned_data[f"variation_{variation.id}"]
        if variation.availability != value:
            variation.availability = value
            variation.save(update_fields=["availability"])
    return HttpResponse()


class VariationsCountForm(forms.Form):
    def __init__(self, variations, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for variation in variations:
            key = f"variation_{variation.pk}"
            self.fields[key] = forms.IntegerField(
                required=False,
                initial=None,
                widget=forms.NumberInput(
                    attrs={
                        "placeholder": variation.count or "",
                    }
                ),
            )

    def field_for_rendering_by_variation(self, variation):
        key = f"variation_{variation.pk}"
        return self[key]


@login_required()
@require_http_methods(["GET", "POST"])
def variation_count_config(request, product_id=None):
    products = Product.objects.all()
    if product_id is not None:
        products = products.filter(id=product_id)
    variations = list(SizeVariation.objects.filter(design_variation__product__in=products).all())

    form = VariationsCountForm(variations, request.POST or None)

    def render_variation_form(variation):
        field = form.field_for_rendering_by_variation(variation)
        return render_to_string(
            "counting/variation_count_box.html",
            context={"field": field, "variation": variation},
            request=request,
        )

    def render_empty_form(product, size):
        return ""

    open_status = get_current_open_status()
    current_event = open_status.event if open_status else Event.objects.order_by("-day_1").first()
    tables = [
        table
        for event_groups, label in [
            ({current_event}, current_event.name),
            (set(Event.objects.all()) - {current_event}, "old"),
        ]
        for product in products
        if (
            table := ProductTable(
                title=f"{label} {product.name}",
                product=product,
                only_events_in=event_groups,
                render_variation=render_variation_form,
                render_empty=render_empty_form,
                show_empty_rows=False,
                table_class="count-config-table",
            )
        ).rows
    ]

    if request.POST and form.is_valid():
        now = timezone.now()
        items_changed = 0

        for key, value in form.cleaned_data.items():
            variation_id = int(key.rsplit("_", 1)[-1])
            variation = get_object_or_404(SizeVariation, id=variation_id)
            if value is not None and variation.count != value:
                variation.count = value
                variation.count_reserved_until = None
                variation.count_disabled_until = None
                variation.count_disabled_reason = None
                variation.counted_at = now
                variation.count_prio_bumped = False
                variation.save()

                CountEvent(
                    count=value,
                    variation=variation,
                    name=request.user.username,
                ).save()

                items_changed += 1

        messages.info(request, f"Updated {items_changed} item counts.")
        return (
            redirect("variation_count_config", product_id)
            if product_id
            else redirect("variation_count_config")
        )

    context = {"tables": tables}
    return render(request, "operator/variation_count_config.html", context)


@login_required()
@require_GET
def operator_overview(request):
    product_categories = [
        {
            "product_category": product_category,
            "products": product_category.products.all(),
        }
        for product_category in ProductCategory.objects.all()
    ]

    context = {
        "product_categories": product_categories,
        "last_open_status": get_current_open_status(),
        "upcoming_open_status": OpenStatus.objects.filter(datetime__gte=timezone.now()).order_by(
            "datetime"
        ),
    }
    return render(request, "operator/operator_overview.html", context)


@login_required()
@require_GET
def variation_availability_event_list(request):
    return render(
        request,
        "variation_availability_event_list.html",
        {"change_events": AvailabilityEvent.objects.order_by("-datetime")},
    )


class EventPricesForm(forms.Form):
    def _get_price_field(self, label, initial, help_text=None):
        return forms.DecimalField(
            label=label,
            decimal_places=2,
            max_digits=10,
            min_value=0,
            initial=initial,
            required=initial is not None,  # cannot delete price
            help_text=help_text,
        )

    def _get_key(self, event_id, product):
        return f"event-{event_id}-product-{product.id}"

    def __init__(self, *args, event=None, **kwargs):
        self.event = event

        super().__init__(*args, **kwargs)

        self.products = Product.objects.all()
        self.current_products_keys = []
        self.old_products_keys = []
        self.old_events = Event.objects.all().exclude(id=self.event.id)
        for product in self.products:
            # current event
            if DesignVariation.objects.filter(product=product, design__event=self.event).exists():
                help_text = None
                try:
                    initial = Price.objects.get(
                        product=product,
                        valid_at=self.event,
                        valid_for_products_from_event=self.event,
                    ).amount
                except Price.DoesNotExist:
                    initial = None
                    help_text = "not set"

                key = self._get_key(self.event.id, product)
                self.fields[key] = self._get_price_field(
                    label=f"{self.event!s} {product!s}", initial=initial, help_text=help_text
                )
                self.current_products_keys.append(key)
            else:
                self.current_products_keys.append(None)
            # old events
            if DesignVariation.objects.filter(
                product=product, design__event__in=self.old_events
            ).exists():
                prices = Price.objects.filter(
                    product=product,
                    valid_at=self.event,
                    valid_for_products_from_event__in=self.old_events,
                ).aggregate(min=Min("amount"), max=Max("amount"))
                min_amount, max_amount = prices["min"], prices["max"]
                initial = None
                help_text = "not set"
                if min_amount is not None and min_amount == max_amount:
                    initial = min_amount
                    help_text = None
                elif min_amount != max_amount:
                    help_text = f"ranges from {min_amount} to {max_amount}"
                key = self._get_key("old", product)
                self.fields[key] = self._get_price_field(
                    label=f"old {product!s}", initial=initial, help_text=help_text
                )
                self.old_products_keys.append(key)
            else:
                self.old_products_keys.append(None)

    def iter_product_current_old_fields(self):
        for product, current_key, old_key in zip(
            self.products, self.current_products_keys, self.old_products_keys
        ):
            yield (
                product,
                self[current_key] if current_key else None,
                self[old_key] if old_key else None,
            )

    def save(self):
        created_count, changed_count = 0, 0
        for product, current_key, old_key in zip(
            self.products, self.current_products_keys, self.old_products_keys
        ):
            if current_key and (amount := self.cleaned_data[current_key]) is not None:
                price, created = Price.objects.get_or_create(
                    product=product,
                    valid_at=self.event,
                    valid_for_products_from_event=self.event,
                    defaults={"amount": amount},
                )
                created_count += created
                if not created and price.amount != amount:
                    changed_count += 1
                    price.amount = amount
                    price.save(update_fields=["amount"])

            if old_key and (amount := self.cleaned_data[old_key]) is not None:
                for old_event in self.old_events:
                    price, created = Price.objects.get_or_create(
                        product=product,
                        valid_at=self.event,
                        valid_for_products_from_event=old_event,
                        defaults={"amount": amount},
                    )
                    created_count += created
                    if not created and price.amount != amount:
                        changed_count += 1
                        price.amount = amount
                        price.save(update_fields=["amount"])
        return created_count, changed_count


class EventPricesConfigView(FormView):
    form_class = EventPricesForm
    template_name = "operator/event_prices_config.html"

    def form_valid(self, form):
        created_count, changed_count = form.save()
        messages.success(self.request, f"Created {created_count}, changed {changed_count} prices.")
        return HttpResponseRedirect(reverse("operator_overview"))

    def get_form_kwargs(self):
        return {
            "event": get_current_open_status().event,
            **super().get_form_kwargs(),
        }
