import csv
import io
from os import access
from django.contrib import admin
from django.http import HttpResponse
from django.urls import path
from django.shortcuts import reverse, get_object_or_404
from django.utils.html import format_html

from hagrid.products.pdf_code import generate_access_code_pdf

from .models import *

admin.site.register(StoreSettings)
admin.site.register(Variation)
admin.site.register(SizeGroup)
admin.site.register(VariationAvailabilityEvent)
admin.site.register(ProductGroup)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "price", "position", "product_group"]
    list_editable = ["price", "position", "product_group"]
    list_filter = ["product_group"]


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ["name", "group"]
    list_display_links = ["name"]
    list_filter = ["group"]

@admin.register(VariationCountEvent)
class VariationCountEventAdmin(admin.ModelAdmin):
    list_display = ["__str__", "datetime", "variation", "name", "comment", "count"]
    list_filter = ["variation__product", "variation__size__name", "variation__size__group"]

    actions = ('export_csv',)

    def export_csv(self, request, queryset):
        events = queryset.all()

        filename = "variation-count-events.csv"

        with io.StringIO() as buffer:
            writer = csv.writer(buffer)
            writer.writerow([
                'datetime',
                'product',
                'sizegroup'
                'size',
                'comment',
                'count',
            ])
            for event in events:
                variation = event.variation
                writer.writerow([
                    event.datetime.strftime('%Y-%m-%d %H:%M:%S'),
                    str(variation.product),
                    str(variation.size.group),
                    str(variation.size.name),
                    str(event.comment),
                    str(event.count),
                ])
            data = buffer.getvalue()


        response = HttpResponse(data, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        return response

@admin.register(VariationCountAccessCode)
class VariationCountAccessCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "description", "as_queue", "code_actions")
    actions = ('make_pdf',)

    def description(self, obj):
        return str(obj)  # here you can do whatever you want

    def code_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">PDF</a>',
            reverse("admin:products_variationcountaccesscode_add", args=[obj.pk]),
        )

    code_actions.short_description = "Actions"
    code_actions.allow_tags = True

    def get_urls(self):
        return [
            path(
                "<path:object_id>/pdf/",
                self.admin_site.admin_view(self.process_pdf),
                name="products_variationcountaccesscode_add",
            ),
            *super().get_urls(),
        ]

    def process_pdf(self, request, object_id):
        return self.make_pdf(request, VariationCountAccessCode.objects.filter(pk=object_id))

    def make_pdf(self, request, queryset):
        access_codes = queryset.all()

        if len(access_codes) == 1:
            filename = f"c3foc-counting-code-{access_codes[0]}.pdf"
        else:
            filename = f"c3foc-{len(access_codes)}-counting-codes.pdf"
        data = generate_access_code_pdf(request, access_codes, filename)

        response = HttpResponse(data, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        return response
