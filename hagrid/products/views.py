from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render, get_object_or_404
from django.template.loader import render_to_string
from django.views import View
from django.views.generic import TemplateView

from hagrid.gallery.models import GalleryImage

from .models import Product, ProductGroup, Size, SizeGroup, Variation, VariationAvailabilityEvent


class SizeTable:
    def __init__(self, sizegroup, render_variation=None, render_empty=None, show_empty_rows=False):
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
        return [self.sizegroup.name] + [size.name for size in self.sizegroup.sizes.all()]

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
        self.fields['exist'].widget.attrs.update({'style': 'display: none'})
        self.fields['initial_amount'].widget.attrs.update({'style': 'width: 10ch;', 'placeholder': 'Initial'})
        self.fields['availability'].widget = forms.RadioSelect(choices=Variation.AVAILABILITY_STATES, attrs={'style': 'position:fixed;opacity:0;'})
        self.fields['product'].widget = forms.NumberInput()
        self.fields['size'].widget = forms.NumberInput()

    class Meta:
        model = Variation
        exclude = []

class VariationConfigView(LoginRequiredMixin, View):

    def post(self, request):
        variation_tables, forms = self.get_variation_tables_and_forms(request)
        for form in forms:
            if form.is_valid():
                if form.cleaned_data['exist']:
                    variation, created= Variation.objects.get_or_create(
                            product=form.cleaned_data['product'],
                            size=form.cleaned_data['size'],
                    )
                    variation.availability = form.cleaned_data['availability']
                    variation.initial_amount = form.cleaned_data['initial_amount']
                    variation.save()
                else:
                    Variation.objects.filter(product=form.cleaned_data['product'], size=form.cleaned_data['size']).delete()
        return redirect('availabilityconfig')

    def get_variation_tables_and_forms(self, request):
        forms = []

        def render_form(form):
            return render_to_string('variation_config_box.html', context={'form': form}, request=request)
        def render_variation_form(variation):
            prefix = "existing_{}".format(variation.id)
            if request.POST:
                form = VariationConfigForm(request.POST, prefix=prefix)
            else:
                form = VariationConfigForm(prefix=prefix, initial={'exist': True}, instance=variation)
            forms.append(form)
            return render_form(form)
        def render_empty_form(product, size):
            prefix = "new_{}_{}".format(product.id, size.id)
            if request.POST:
                form = VariationConfigForm(request.POST, prefix=prefix)
            else:
                form = VariationConfigForm(prefix=prefix, initial={'product': product, 'size': size, 'exist': False})
            forms.append(form)
            return render_form(form)

        tables = [SizeTable(sizegroup,
                            render_variation=render_variation_form,
                            render_empty=render_empty_form,
                            show_empty_rows=True)
            for sizegroup in SizeGroup.objects.all()]
        return tables, forms

    def get(self, request):
        variation_tables, variation_forms = self.get_variation_tables_and_forms(request)
        context = {
                'products': Product.objects.all(),
                'variation_tables': variation_tables,
        }
        return render(request, "productconfig.html", context)




class VariationsAvailabilityForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for variation in Variation.objects.all():
            key = 'variation_{}'.format(variation.pk)
            self.fields[key] = forms.ChoiceField(
                    choices=Variation.AVAILABILITY_STATES,
                    initial=variation.availability,
                    widget=forms.RadioSelect(
                        choices=Variation.AVAILABILITY_STATES,
                        attrs={'style': 'position:fixed;opacity:0;'}),
            )

    def field_for_rendering_by_variation(self, variation):
        key = 'variation_{}'.format(variation.pk)
        return self[key]


class VariationChangeAvailabilityView(LoginRequiredMixin, View):


    def get_variation_tables_and_form(self, request):
        form = VariationsAvailabilityForm(request.POST or None)

        def render_variation_form(variation):
            field = form.field_for_rendering_by_variation(variation)
            return render_to_string('variation_availability_box.html', context={'field': field}, request=request)
        def render_empty_form(product, size):
            return ""

        tables = [SizeTable(sizegroup,
                            render_variation=render_variation_form,
                            render_empty=render_empty_form,
                            show_empty_rows=False)
            for sizegroup in SizeGroup.objects.all()]
        return tables, form

    def post(self, request):
        return self.get(request)

    def get(self, request):
        variation_tables, form = self.get_variation_tables_and_form(request)

        if form.is_valid():
            for key, value in form.cleaned_data.items():
                variation_id = int(key.rsplit("_", 1)[-1])
                variation = get_object_or_404(Variation, id=variation_id)
                variation.availability = value
                variation.save()

        context = {
                'products': Product.objects.all(),
                'variation_tables': variation_tables,
        }
        return render(request, "availabilityconfig.html", context)


class VariationAvailabilityEventListView(LoginRequiredMixin, TemplateView):
    template_name = "variationavailabilityeventlist.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['change_events'] = VariationAvailabilityEvent.objects.order_by('-datetime')
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
            variations = product_variations.filter(size__group=sizegroup).distinct()

            return {
                "sizegroup": sizegroup,
                "variations": variations,
            }

        def _transform_product(product):
            variations = all_variations.filter(product=product)
            sizegroups = all_sizegroups.filter(sizes__variations__product=product).distinct()
            images = GalleryImage.objects.filter(variation__product=product)[:1]
            return {
                "product": product,
                "sizegroups": [_transform_sizegroup(sizegroup, variations) for sizegroup in sizegroups],
                "image": images[0] if images else None,
            }

        def _transform_product_group(product_group):
            products = all_products.filter(product_group=product_group)

            return {
                "product_group": product_group,
                "products": list(_transform_product(p) for p in products)
            }

        return list(_transform_product_group(pg) for pg in product_groups)

class DashboardView(TemplateView):

    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = Product.objects.all()
        context['sizes'] = Size.objects.all()
        context['sizegroups'] = SizeGroup.objects.all()
        context['variations'] = Variation.objects.all()
        context['availability_tables'] = [SizeTable(sg, render_variation=render_variation_to_colorful_html) for sg in SizeGroup.objects.all()]
        context['product_availabilities'] = ProductAvailabilityView()
        return context

class DashboardTableView(TemplateView):

    template_name = "dashboard_table.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = Product.objects.all()
        context['sizes'] = Size.objects.all()
        context['sizegroups'] = SizeGroup.objects.all()
        context['variations'] = Variation.objects.all()
        context['availability_tables'] = [SizeTable(sg, render_variation=render_variation_to_colorful_html) for sg in SizeGroup.objects.all()]
        context['product_availabilities'] = ProductAvailabilityView()
        return context
