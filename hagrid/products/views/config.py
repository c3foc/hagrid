from datetime import datetime

from django import forms
from django.views.decorators.http import require_GET, require_http_methods
from django.contrib.auth.views import login_required
from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from django.template.loader import render_to_string

from ..models import (
    Product,
    ProductGroup,
    Variation,
    VariationAvailabilityEvent,
    VariationCountEvent,
)

from ..tables import ProductTable


class VariationConfigForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["initial_amount"].blank = True
        self.fields["initial_amount"].initial = None
        self.fields["initial_amount"].required = False
        self.fields["product"].widget = forms.HiddenInput()
        self.fields["size"].widget = forms.HiddenInput()

    class Meta:
        model = Variation
        fields = ["initial_amount", "product", "size"]


@login_required()
@require_http_methods(["GET", "POST"])
def variation_config(request, product_id=None):
    products = list(
        Product.objects.all()
        if product_id is None
        else Product.objects.filter(id=product_id)
    )

    variation_forms = []

    def render_form(form, variation=None):
        return render_to_string(
            "variation_config_box.html", context={"form": form}, request=request
        )

    def render_variation_form(variation):
        prefix = f"variation-{variation.product.id}-{variation.size.id}"
        if request.POST:
            form = VariationConfigForm(request.POST, prefix=prefix)
        else:
            form = VariationConfigForm(prefix=prefix, instance=variation)
        variation_forms.append(form)
        return render_form(form, variation)

    def render_empty_form(product, size):
        prefix = f"variation-{product.id}-{size.id}"
        if request.POST:
            form = VariationConfigForm(request.POST, prefix=prefix)
        else:
            form = VariationConfigForm(
                prefix=prefix,
                initial={"product": product, "size": size},
            )
        variation_forms.append(form)
        return render_form(form)

    product_tables = [
        ProductTable(
            product,
            render_variation=render_variation_form,
            render_empty=render_empty_form,
            show_empty_rows=True,
        )
        for product in products
    ]

    if request.POST and all(map(lambda f: f.is_valid(), variation_forms)):
        changed_count = 0
        created_count = 0
        deleted_count = 0

        for form in variation_forms:
            initial_amount = form.cleaned_data["initial_amount"]
            if initial_amount is not None:
                variation, created = Variation.objects.get_or_create(
                    product=form.cleaned_data["product"],
                    size=form.cleaned_data["size"],
                    defaults={
                        "initial_amount": initial_amount,
                        "availability": Variation.STATE_MANY_AVAILABLE,
                    },
                )
                if not created and variation.initial_amount != initial_amount:
                    changed_count += 1
                    variation.initial_amount = initial_amount
                    variation.save()
                elif created:
                    created_count += 1
            else:
                del_count, _ = Variation.objects.filter(
                    product=form.cleaned_data["product"],
                    size=form.cleaned_data["size"],
                ).delete()
                deleted_count += del_count

        total_count = changed_count + created_count + deleted_count
        messages.add_message(
            self.request,
            messages.SUCCESS,
            f"Changed {total_count} variations (created {created_count}, modified {changed_count}, deleted {deleted_count})",
        )

        return redirect("products_config_overview")

    return render(
        request,
        "variation_config.html",
        {
            "products": products,
            "product_tables": product_tables,
        },
    )


class VariationsAvailabilityForm(forms.Form):
    def __init__(self, variations, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for variation in variations:
            key = "variation_{}".format(variation.pk)
            self.fields[key] = forms.ChoiceField(
                choices=Variation.AVAILABILITY_STATES,
                initial=variation.availability,
                widget=forms.RadioSelect(
                    choices=Variation.AVAILABILITY_STATES,
                    attrs={"style": "position:fixed;opacity:0;"},
                ),
            )

    def field_for_rendering_by_variation(self, variation):
        key = "variation_{}".format(variation.pk)
        return self[key]


@login_required()
def variation_availability_config(request, product_id=None):
    products = Product.objects.all()
    if product_id is not None:
        products = products.filter(id=product_id)
    variations = list(Variation.objects.filter(product__in=products).all())

    form = VariationsAvailabilityForm(variations, request.POST or None)

    def render_variation_form(variation):
        field = form.field_for_rendering_by_variation(variation)
        return render_to_string(
            "variation_availability_box.html",
            context={"field": field, "variation": variation},
            request=request,
        )

    def render_empty_form(product, size):
        return ""

    product_tables = {
        product.id: ProductTable(
            product,
            render_variation=render_variation_form,
            render_empty=render_empty_form,
            show_empty_rows=False,
            table_class="availabilities-table",
        )
        for product in products
    }

    if form.is_valid():
        changed_count = 0
        for key, value in form.cleaned_data.items():
            variation_id = int(key.rsplit("_", 1)[-1])
            variation = get_object_or_404(Variation, id=variation_id)
            if variation.availability != value:
                variation.availability = value
                variation.save()
                changed_count += 1
        messages.add_message(
            self.request,
            messages.SUCCESS,
            f"Changed {changed_count} availabilities",
        )

    product_groups = [
        {
            "product_group": product_group,
            "tables": [
                product_tables[product.id]
                for product in product_group.products.all()
                if product.id in product_tables
            ],
        }
        for product_group in ProductGroup.objects.all()
    ]

    unassigned = list(Product.objects.filter(product_group=None))
    if unassigned:
        product_groups.append(
            {
                "product_group": None,
                "tables": [
                    product_tables[product.id]
                    for product in unassigned
                    if product.id in product_tables
                ],
            }
        )

    # filter empty groups
    product_groups = [p for p in product_groups if len(p["tables"])]

    context = {"product_groups": product_groups}
    return render(request, "variation_availability_config.html", context)

class VariationsCountForm(forms.Form):
    def __init__(self, variations, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for variation in variations:
            key = "variation_{}".format(variation.pk)
            self.fields[key] = forms.IntegerField(
                required=False,
                initial=None,
                widget=forms.NumberInput(attrs={
                    'placeholder': variation.count or '',
                }),
            )

    def field_for_rendering_by_variation(self, variation):
        key = "variation_{}".format(variation.pk)
        return self[key]


@login_required()
def variation_count_config(request, product_id=None):
    products = Product.objects.all()
    if product_id is not None:
        products = products.filter(id=product_id)
    variations = list(Variation.objects.filter(product__in=products).all())

    form = VariationsCountForm(variations, request.POST or None)

    def render_variation_form(variation):
        field = form.field_for_rendering_by_variation(variation)
        return render_to_string(
            "variation_count_box.html",
            context={"field": field, "variation": variation},
            request=request,
        )

    def render_empty_form(product, size):
        return ""

    product_tables = {
        product.id: ProductTable(
            product,
            render_variation=render_variation_form,
            render_empty=render_empty_form,
            show_empty_rows=False,
            table_class="count-config-table",
        )
        for product in products
    }

    if request.POST and form.is_valid():
        now = datetime.now()
        items_changed = 0

        for key, value in form.cleaned_data.items():
            variation_id = int(key.rsplit("_", 1)[-1])
            variation = get_object_or_404(Variation, id=variation_id)
            if value is not None and variation.count != value:
                variation.count = value
                variation.count_reserved_until = None
                variation.counted_at = now
                variation.count_prio_bumped = False
                variation.save()

                VariationCountEvent(
                    count=value,
                    variation=variation,
                    name=request.user.username,
                ).save()

                items_changed += 1

        messages.info(request, f"Updated {items_changed} item counts.")
        return redirect('variation_count_config', product_id) if product_id else redirect('variation_count_config')

    product_groups = [
        {
            "product_group": product_group,
            "tables": [
                product_tables[product.id]
                for product in product_group.products.all()
                if product.id in product_tables
            ],
        }
        for product_group in ProductGroup.objects.all()
    ]

    unassigned = list(Product.objects.filter(product_group=None))
    if unassigned:
        product_groups.append(
            {
                "product_group": None,
                "tables": [
                    product_tables[product.id]
                    for product in unassigned
                    if product.id in product_tables
                ],
            }
        )

    # filter empty groups
    product_groups = [p for p in product_groups if len(p["tables"])]

    context = {"product_groups": product_groups}
    return render(request, "variation_count_config.html", context)


@login_required()
@require_GET
def products_config_overview(request):
    product_groups = [
        {
            "product_group": product_group,
            "products": product_group.products.all(),
        }
        for product_group in ProductGroup.objects.all()
    ]

    unassigned = list(Product.objects.filter(product_group=None))
    if unassigned:
        product_groups.append({"product_group": None, "products": unassigned})

    context = {"product_groups": product_groups}
    return render(request, "products_config_overview.html", context)


@login_required()
@require_GET
def variation_availability_event_list(request):
    return render(
        request,
        "variation_availability_event_list.html",
        {"change_events": VariationAvailabilityEvent.objects.order_by("-datetime")},
    )

