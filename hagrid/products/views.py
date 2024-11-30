from datetime import datetime, timedelta

from django import forms
from django.contrib.auth.views import login_required
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http.response import Http404
from django.shortcuts import redirect, render, get_object_or_404, reverse
from django.template.loader import render_to_string
from django.views import View
from django.views.generic import TemplateView

from hagrid.gallery.models import GalleryImage
from hagrid.operations.models import OpenStatus

from .models import (
    Product,
    ProductGroup,
    Size,
    SizeGroup,
    StoreSettings,
    Variation,
    VariationAvailabilityEvent,
    VariationCountAccessCode,
    VariationCountEvent,
)


class ProductTable:
    def __init__(
        self,
        product,
        render_variation=None,
        render_empty=None,
        show_empty_rows=False,
        table_class: str = "",
    ):
        self.product = product
        self.table_class = table_class
        self.show_empty_rows = show_empty_rows
        self.render_variation = render_variation or (lambda v: v.availability)
        self.render_empty = render_empty or (lambda *_args: "")

        self.entries = list(self.generate_entries())
        self.column_count = (
            max(len(entry["sizes"]) for entry in self.entries) if self.entries else 0
        )
        for entry in self.entries:
            entry["fill"] = [""] * (self.column_count - len(entry["sizes"]))

    def generate_entries(self):
        all_variations = Variation.objects.all()
        bool(all_variations)  # cache all variations in queryset
        all_sizegroups = SizeGroup.objects.all()
        bool(all_variations)
        all_sizes = Size.objects.filter(variations__product=self.product).distinct()
        bool(all_sizes)

        for sizegroup in all_sizegroups:
            entry = {"sizegroup": sizegroup, "sizes": []}
            found_variation = False
            for size in sizegroup.sizes.all():
                try:
                    variation = all_variations.get(product=self.product, size=size)
                    entry["sizes"].append(
                        {
                            "size": size,
                            "variation": variation,
                            "html": self.render_variation(variation),
                        }
                    )

                    found_variation = True
                except Variation.DoesNotExist:
                    entry["sizes"].append(
                        {
                            "size": size,
                            "variation": None,
                            "html": self.render_empty(self.product, size),
                        }
                    )

            if found_variation or self.show_empty_rows:
                yield entry

    @property
    def column_width(self):
        return "200"
        # return f"{100/(self.column_count + 1):.1f}%"


class SizeTable:
    def __init__(
        self, sizegroup, render_variation=None, render_empty=None, show_empty_rows=False
    ):
        self.sizegroup = sizegroup
        self.show_empty_rows = show_empty_rows
        if not render_variation:
            render_variation = lambda v: v.availability
        self.render_variation = render_variation
        if not render_empty:
            render_empty = lambda p, s: ""
        self.render_empty = render_empty
        self.entries = self.generate_entries()

    @property
    def header(self):
        return [self.sizegroup.name] + [
            size.name for size in self.sizegroup.sizes.all()
        ]

    def generate_entries(self):
        rows = []
        all_variations = Variation.objects.all()
        bool(all_variations)  # cache all variations in queryset
        sizegroup_sizes = self.sizegroup.sizes.all()

        for product in Product.objects.all():
            row = [product.name]
            found_variation = False
            for size in sizegroup_sizes:
                try:
                    variation = all_variations.get(product=product, size=size)
                    row.append(self.render_variation(variation))
                    found_variation = True
                except Variation.DoesNotExist:
                    row.append(self.render_empty(product, size))
            if found_variation or self.show_empty_rows:
                rows.append(row)
        return rows


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


class VariationConfigView(LoginRequiredMixin, View):
    def get_content(self, request, product_id=None):
        products = list(
            Product.objects.all()
            if product_id is None
            else Product.objects.filter(id=product_id)
        )

        forms = []

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
            forms.append(form)
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
            forms.append(form)
            return render_form(form)

        tables = [
            ProductTable(
                product,
                render_variation=render_variation_form,
                render_empty=render_empty_form,
                show_empty_rows=True,
            )
            for product in products
        ]
        return products, tables, forms

    def get(self, request, product_id=None):
        products, product_tables, variation_forms = self.get_content(
            request, product_id
        )
        context = {
            "products": products,
            "product_tables": product_tables,
        }
        return render(request, "variation_config.html", context)

    def post(self, request, product_id=None):
        _, _, forms = self.get_content(request, product_id)
        changed_count = 0
        created_count = 0
        deleted_count = 0

        # somthing not valid -> render the form again
        if not all(map(lambda f: f.is_valid(), forms)):
            return self.get(request, product_id)

        for form in forms:
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


class VariationAvailabilityConfigView(LoginRequiredMixin, View):
    def get_content(self, request, product_id):
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

        tables = {
            product.id: ProductTable(
                product,
                render_variation=render_variation_form,
                render_empty=render_empty_form,
                show_empty_rows=False,
                table_class="availabilities-table",
            )
            for product in products
        }

        return tables, form

    def post(self, request, product_id=None):
        return self.get(request, product_id)

    def get(self, request, product_id=None):
        product_tables, form = self.get_content(request, product_id)

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

        # filter emtpy groups
        product_groups = [p for p in product_groups if len(p["tables"])]

        context = {"product_groups": product_groups}
        return render(request, "variation_availability_config.html", context)


class ProductsConfigOverviewView(LoginRequiredMixin, View):
    def get(self, request):
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


class VariationAvailabilityEventListView(LoginRequiredMixin, TemplateView):
    template_name = "variationavailabilityeventlist.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["change_events"] = VariationAvailabilityEvent.objects.order_by(
            "-datetime"
        )
        return context


def render_variation_to_colorful_html(variation):
    if variation.availability == Variation.STATE_MANY_AVAILABLE:
        return '<div class="text-center"><span class="badge bg-success">&#10003;</span></div>'
    if variation.availability == Variation.STATE_FEW_AVAILABLE:
        return '<div class="text-center"><span class="badge bg-warning">&#9888;</span></div>'
    if variation.availability == Variation.STATE_SOLD_OUT:
        return '<div class="text-center"><span class="badge bg-danger">&#10007;</span></div>'


class ProductAvailabilityView:
    def __init__(self):
        self.entries = self.generate_entries()

    def generate_entries(self):
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
            images = GalleryImage.objects.filter(variation__product=product)[:1]
            return {
                "product": product,
                "sizegroups": [
                    _transform_sizegroup(sizegroup, variations)
                    for sizegroup in sizegroups
                ],
                "image": images[0] if images else None,
            }

        def _transform_product_group(product_group):
            products = all_products.filter(product_group=product_group)

            return {
                "product_group": product_group,
                "products": list(_transform_product(p) for p in products),
            }

        return list(_transform_product_group(pg) for pg in product_groups)


class DashboardView(TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["products"] = Product.objects.all()
        context["sizes"] = Size.objects.all()
        context["sizegroups"] = SizeGroup.objects.all()
        context["variations"] = Variation.objects.all()
        context["product_availabilities"] = ProductAvailabilityView()

        dashboard_text: str | None = StoreSettings.objects.first().dashboard_text
        if dashboard_text and "%open_status%" in dashboard_text:
            open_status = render_to_string(
                "open_status.html", {"open_status": OpenStatus.get_status()}
            )
            dashboard_text = dashboard_text.replace("%open_status%", open_status)

        context["dashboard_text"] = dashboard_text

        return context


class DashboardTableView(TemplateView):
    template_name = "dashboard_table.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["products"] = Product.objects.all()
        context["sizes"] = Size.objects.all()
        context["sizegroups"] = SizeGroup.objects.all()
        context["variations"] = Variation.objects.all()
        context["availability_tables"] = [
            SizeTable(sg, render_variation=render_variation_to_colorful_html)
            for sg in SizeGroup.objects.all()
        ]
        return context


class VariationCountForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["count"].widget = forms.NumberInput()

    class Meta:
        model = VariationCountEvent
        exclude = ["datetime", "variation", "comment", "name"]


class VariationCountCommonForm(forms.Form):
    name = forms.CharField(
        label="Nickname",
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "optional, see tutorial",
                "data-synclocalstorage": "nickname",
            }
        ),
    )
    comment = forms.CharField(
        label="Comment",
        max_length=250,
        required=False,
        widget=forms.Textarea(attrs={"rows": "2"}),
    )


def variation_count_view(request, code, variation_id=None):
    if not StoreSettings.objects.first().counting_enabled:
        messages.add_message(
            self.request, messages.ERROR, "We are not counting items at the moment."
        )
        return redirect("dashboard")

    access_code = get_object_or_404(VariationCountAccessCode, code=code, disabled=False)

    if access_code.as_queue:
        if not variation_id:
            form = forms.Form(request.POST or None)

            datetime_to_event_time = OpenStatus.make_datetime_to_event_time()
            priorities = []
            available_variations = access_code.variations.filter(
                Q(count_reserved_until__isnull=True)
                | Q(count_reserved_until__lt=datetime.now())
            )
            if not available_variations:
                messages.add_message(
                    request,
                    messages.INFO,
                    "Nothing to count at the moment, please come back later.",
                )
            else:
                for variation in available_variations:
                    priorities.append(
                        {
                            "variation": variation,
                            **variation.get_count_priority(datetime_to_event_time),
                        }
                    )

                priorities = sorted(priorities, key=lambda s: s["total"], reverse=True)

                if request.POST and form.is_valid():
                    top_prio = priorities[0]
                    variation = top_prio["variation"]
                    variation.count_reserved_until = datetime.now() + timedelta(
                        minutes=5
                    )
                    variation.save()

                    # assign a variation and redirect
                    return redirect("variationcount", code, variation.id)

                important = sum(map(lambda p: int(p["total"] >= 0.2), priorities), 0)

                return render(
                    request,
                    "variation_count_queue.html",
                    {
                        "form": form,
                        "total_variations": len(priorities),
                        "high_prio_variations": important,
                    },
                )

        try:
            variations = [access_code.variations.get(id=variation_id)]
        except Variation.DoesNotExist:
            raise Http404()

    elif variation_id:
        raise Http404()
    else:
        variations = list(access_code.variations)

    common_form = VariationCountCommonForm(request.POST or None)
    items = [
        {
            "variation": variation,
            "form": VariationCountForm(
                request.POST or None, prefix="variation_{}".format(variation.id)
            ),
        }
        for variation in variations
    ]

    common_name = []
    products_used = list(Product.objects.filter(variations__in=variations).distinct())
    product_column = len(products_used) > 1
    if not product_column:
        common_name.append(str(products_used[0]))

    sizegroups_used = list(
        SizeGroup.objects.filter(sizes__variations__in=variations).distinct()
    )
    sizegroup_column = len(sizegroups_used) > 1
    if not sizegroup_column:
        common_name.append(str(sizegroups_used[0]))

    sizes_used = list(Size.objects.filter(variations__in=variations).distinct())
    size_column = len(sizes_used) > 1
    if not size_column:
        common_name.append(str(sizes_used[0]))

    if request.POST:
        now = datetime.now()

        if common_form.is_valid() and all(map(lambda i: i["form"].is_valid(), items)):
            total = 0
            items_changed = 0

            for item in items:
                form = item["form"]
                variation = item["variation"]
                count = form.cleaned_data["count"]
                if count is not None:
                    variation.count = count
                    variation.count_reserved_until = None
                    variation.counted_at = now
                    variation.count_prio_bumped = False
                    variation.save()
                    total += count
                    items_changed += 1

                    VariationCountEvent(
                        count=count,
                        variation=variation,
                        comment=common_form.cleaned_data["comment"],
                        name=common_form.cleaned_data["name"],
                    ).save()

            if access_code.as_queue:
                messages.add_message(
                    request,
                    messages.INFO,
                    "Thank you for counting this item. You can do another if you want!",
                )
                return redirect("variationcount", code)
            return redirect(
                reverse("variation_count_success")
                + f"?total={total}&items_changed={items_changed}"
            )

    if variation_id:
        return render(
            request,
            "variation_count_from_queue.html",
            {
                "access_code": access_code,
                "variation": items[0]["variation"],
                "form": items[0]["form"],
                "common_form": common_form,
            },
        )

    return render(
        request,
        "variation_count.html",
        {
            "product_column": product_column,
            "sizegroup_column": sizegroup_column,
            "size_column": size_column,
            "column_count": product_column + sizegroup_column + size_column,
            "common_name": " / ".join(common_name),
            "access_code": access_code,
            "items": items,
            "common_form": common_form,
        },
    )


class VariationCountSuccessView(View):
    template_name = "variation_count_success.html"

    def get(self, request):
        try:
            total = int(request.GET.get("total"))
            items_changed = int(request.GET.get("items_changed"))
        except (ValueError, TypeError) as _e:
            raise Http404()

        return render(
            request,
            "variation_count_success.html",
            {
                "total": total,
                "items_changed": items_changed,
            },
        )


class VariationBumpForm(forms.Form):
    variation = forms.IntegerField(widget=forms.HiddenInput())
    action = forms.ChoiceField(
        choices=[
            ("bump", "Bump"),
            ("unbump", "Unbump"),
        ]
    )


@login_required()
def variation_count_overview_view(request):
    datetime_to_event_time = OpenStatus.make_datetime_to_event_time()

    priorities = []
    for variation in Variation.objects.all():
        prefix = f"variation-{variation.id}"
        form = (
            VariationBumpForm(request.POST, prefix=prefix)
            if request.POST
            else VariationBumpForm(prefix=prefix, initial={"variation": variation.id})
        )

        priorities.append(
            {
                "variation": variation,
                **variation.get_count_priority(datetime_to_event_time),
                "form": form,
            }
        )

    if request.POST:
        for priority in priorities:
            form = priority["form"]
            variation = priority["variation"]
            if form.is_valid() and variation.id == form.cleaned_data["variation"]:
                variation.count_prio_bumped = form.cleaned_data["action"] == "bump"
                variation.save()
                messages.info(
                    request,
                    str(variation)
                    + (" bumped" if variation.count_prio_bumped else " unbumped"),
                )
                return redirect('variation_count_overview')

    priorities = sorted(priorities, key=lambda s: s["total"], reverse=True)

    context = {"priorities": priorities}
    return render(request, "variation_count_overview.html", context)
