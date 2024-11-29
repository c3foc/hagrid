from datetime import datetime

from django import forms
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
        self, product, render_variation=None, render_empty=None, show_empty_rows=False
    ):
        self.product = product
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
    exist = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["exist"].widget.attrs.update({"style": "display: none"})
        self.fields["initial_amount"].widget.attrs.update(
            {"style": "width: 10ch;", "placeholder": "Initial"}
        )
        self.fields["availability"].widget = forms.RadioSelect(
            choices=Variation.AVAILABILITY_STATES,
            attrs={"style": "position:fixed;opacity:0;"},
        )
        self.fields["product"].widget = forms.NumberInput()
        self.fields["size"].widget = forms.NumberInput()

    class Meta:
        model = Variation
        exclude = []


class VariationConfigView(LoginRequiredMixin, View):
    def post(self, request):
        variation_tables, forms = self.get_variation_tables_and_forms(request)
        for form in forms:
            if form.is_valid():
                if form.cleaned_data["exist"]:
                    variation, created = Variation.objects.get_or_create(
                        product=form.cleaned_data["product"],
                        size=form.cleaned_data["size"],
                    )
                    variation.availability = form.cleaned_data["availability"]
                    variation.initial_amount = form.cleaned_data["initial_amount"]
                    variation.save()
                else:
                    Variation.objects.filter(
                        product=form.cleaned_data["product"],
                        size=form.cleaned_data["size"],
                    ).delete()
        return redirect("availabilityconfig")

    def get_variation_tables_and_forms(self, request):
        forms = []

        def render_form(form, variation=None):
            return render_to_string(
                "variation_config_box.html", context={"form": form}, request=request
            )

        def render_variation_form(variation):
            prefix = "existing_{}".format(variation.id)
            if request.POST:
                form = VariationConfigForm(request.POST, prefix=prefix)
            else:
                form = VariationConfigForm(
                    prefix=prefix, initial={"exist": True}, instance=variation
                )
            forms.append(form)
            return render_form(form, variation)

        def render_empty_form(product, size):
            prefix = "new_{}_{}".format(product.id, size.id)
            if request.POST:
                form = VariationConfigForm(request.POST, prefix=prefix)
            else:
                form = VariationConfigForm(
                    prefix=prefix,
                    initial={"product": product, "size": size, "exist": False},
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
            for product in Product.objects.all()
        ]
        return tables, forms

    def get(self, request):
        product_tables, variation_forms = self.get_variation_tables_and_forms(request)
        context = {
            "products": Product.objects.all(),
            "product_tables": product_tables,
        }
        return render(request, "productconfig.html", context)


class VariationsAvailabilityForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for variation in Variation.objects.all():
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


class VariationChangeAvailabilityView(LoginRequiredMixin, View):
    def get_product_tables_and_forms(self, request):
        form = VariationsAvailabilityForm(request.POST or None)

        def render_variation_form(variation):
            field = form.field_for_rendering_by_variation(variation)
            return render_to_string(
                "variation_availability_box.html",
                context={"field": field},
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
            )
            for product in Product.objects.all()
        }

        return tables, form

    def post(self, request):
        return self.get(request)

    def get(self, request):
        product_tables, form = self.get_product_tables_and_forms(request)

        if form.is_valid():
            for key, value in form.cleaned_data.items():
                variation_id = int(key.rsplit("_", 1)[-1])
                variation = get_object_or_404(Variation, id=variation_id)
                variation.availability = value
                variation.save()

        product_groups = [
            {
                "product_group": product_group,
                "tables": [
                    product_tables.get(product.id)
                    for product in product_group.products.all()
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
                        product_tables.get(product.id) for product in unassigned
                    ],
                }
            )

        context = {"product_groups": product_groups}
        return render(request, "availabilityconfig.html", context)


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

        dashboard_text: str|None = StoreSettings.objects.first().dashboard_text
        if dashboard_text and '%open_status%' in dashboard_text:
            open_status = render_to_string('open_status.html', {'open_status': OpenStatus.get_status()})
            dashboard_text = dashboard_text.replace('%open_status%', open_status)

        context['dashboard_text'] = dashboard_text

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


class VariationCountView(View):
    template_name = "variation_count.html"

    def get_content(self, request, code):
        access_code = get_object_or_404(VariationCountAccessCode, code=code, disabled=False)

        variation_query = Variation.objects

        products = access_code.products.all()
        if products:
            variation_query = variation_query.filter(product__in=products)

        sizes = access_code.sizes.all()
        if sizes:
            variation_query = variation_query.filter(size__in=sizes)

        sizegroups = access_code.sizegroups.all()
        if sizegroups:
            variation_query = variation_query.filter(size__group__in=sizegroups)

        variation_query = variation_query.order_by('product__product_group__position', 'product__position', 'size__group__position', 'size__position')

        def get_form(variation):
            prefix = "variation_{}".format(variation.id)
            if request.POST:
                return VariationCountForm(request.POST, prefix=prefix)
            else:
                return VariationCountForm(prefix=prefix)


        variations = list(variation_query.distinct())
        items = [
            {"variation": variation, "form": get_form(variation)}
            for variation in variations
        ]

        common_name = []

        products_used = list(
            Product.objects.filter(variations__in=variation_query).distinct()
        )
        product_column = len(products_used) > 1
        if not product_column:
            common_name.append(str(products_used[0]))

        sizegroups_used = list(
            SizeGroup.objects.filter(sizes__variations__in=variation_query).distinct()
        )
        sizegroup_column = len(sizegroups_used) > 1
        if not sizegroup_column:
            common_name.append(str(sizegroups_used[0]))

        sizes_used = list(
            Size.objects.filter(variations__in=variation_query).distinct()
        )
        size_column = len(sizes_used) > 1
        if not size_column:
            common_name.append(str(sizes_used[0]))

        return (
            access_code,
            items,
            {
                "product_column": product_column,
                "sizegroup_column": sizegroup_column,
                "size_column": size_column,
                "column_count": product_column + sizegroup_column + size_column,
                "common_name": " / ".join(common_name),
            },
        )

    def get(self, request, code):
        if not StoreSettings.objects.first().counting_enabled:
            messages.add_message(self.request, messages.ERROR, 'We are not counting items at the moment.')
            return redirect('dashboard')

        access_code, items, ctx = self.get_content(request, code)
        common_form = VariationCountCommonForm()

        return render(
            request,
            self.template_name,
            {
                **ctx,
                "access_code": access_code,
                "items": items,
                "common_form": common_form,
            },
        )

    def post(self, request, code):
        if not StoreSettings.objects.first().counting_enabled:
            messages.add_message(self.request, messages.ERROR, 'We are not counting items at the moment.')
            return redirect('dashboard')

        access_code, items, ctx = self.get_content(request, code)
        common_form = VariationCountCommonForm(request.POST)

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
                    variation.counted_at = now
                    variation.save()
                    total += count
                    items_changed += 1

                    VariationCountEvent(
                        count=count,
                        variation=variation,
                        comment=common_form.cleaned_data["comment"],
                        name=common_form.cleaned_data["name"],
                    ).save()
            return redirect(
                reverse("variation_count_success")
                + f"?total={total}&items_changed={items_changed}"
            )

        return render(
            request,
            self.template_name,
            {
                **ctx,
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
