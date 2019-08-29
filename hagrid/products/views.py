from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.views import View
from django.views.generic import TemplateView

from .models import Product, Size, SizeGroup, Variation


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
        for product in Product.objects.all():
            row = [product.name]
            found_variation = False
            for size in self.sizegroup.sizes.all():
                try:
                    variation = Variation.objects.get(product=product, size=size)
                    row.append(self.render_variation(variation))
                    found_variation = True
                except Variation.DoesNotExist:
                    row.append(self.render_empty(product, size))
            if found_variation or self.show_empty_rows:
                rows.append(row)
        return rows


def render_variation_to_colorful_html(variation):
    if variation.availability == Variation.STATE_SUBMITTED:
        return '<div class="text-center"><span class="badge badge-success">&#10003;</span></div>'
    if variation.availability == Variation.STATE_FEW_AVAILABLE:
        return '<div class="text-center"><span class="badge badge-warning">&#9888;</span></div>'
    if variation.availability == Variation.STATE_SOLD_OUT:
        return '<div class="text-center"><span class="badge badge-danger">&#10007;</span></div>'



class VariationConfigForm(forms.ModelForm):
    exist = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['exist'].widget.attrs.update({'style': 'display: none'})
        self.fields['initial_amount'].widget.attrs.update({'style': 'width: 10ch;'})
        self.fields['availability'].widget = forms.RadioSelect(choices=Variation.AVAILABILITY_STATES, attrs={'style': 'position:fixed;opacity:0;'})

    class Meta:
        model = Variation
        exclude = []


class ProductConfigView(LoginRequiredMixin, View):

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
        return redirect('productconfig')

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

class DashboardView(TemplateView):

    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = Product.objects.all()
        context['sizes'] = Size.objects.all()
        context['sizegroups'] = SizeGroup.objects.all()
        context['variations'] = Variation.objects.all()
        context['availability_tables'] = [SizeTable(sg, render_variation=render_variation_to_colorful_html) for sg in SizeGroup.objects.all()]
        return context
