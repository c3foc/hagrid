import csv
import io

from django.contrib import admin
from django.http import HttpResponse
from django.shortcuts import redirect, reverse
from django.urls import path
from django.utils.html import format_html

from hagrid.products.pdf_code import generate_access_code_pdf

from .models import *

admin.site.register(StoreSettings)
admin.site.register(SizeScale)
admin.site.register(AvailabilityEvent)
admin.site.register(ProductCategory)
admin.site.register(DesignVariation)
admin.site.register(Design)
admin.site.register(Price)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "position", "category"]
    list_editable = ["position", "category"]
    list_filter = ["category"]


@admin.register(SizeVariation)
class SizeVariationAdmin(admin.ModelAdmin):
    list_display = [
        "__str__",
        "design_variation",
        "size",
        "amount_initial",
        "amount_preordered",
        "count",
        "availability",
    ]
    list_editable = []
    list_filter = ["design_variation__design__event", "design_variation__product"]


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ["name", "scale", "position"]
    list_filter = ["scale"]


@admin.register(CountEvent)
class CountEventAdmin(admin.ModelAdmin):
    list_display = ["datetime", "variation", "name", "comment", "count"]
    list_filter = [
        "variation__design_variation",
        "variation__design_variation__design__event",
    ]

    actions = (
        "export_csv",
        "clear_name",
    )

    def clear_name(self, request, queryset):
        queryset.update(name="")
        return redirect("admin:products_variationcountevent_changelist")

    def export_csv(self, request, queryset):
        events = queryset.all()

        filename = "variation-count-events.csv"

        with io.StringIO() as buffer:
            writer = csv.writer(buffer)
            writer.writerow([
                "datetime",
                "product",
                "SizeScalesize",
                "comment",
                "count",
            ])
            for event in events:
                variation = event.variation
                writer.writerow([
                    event.datetime.strftime("%Y-%m-%d %H:%M:%S"),
                    str(variation.product),
                    str(variation.size.group),
                    str(variation.size.name),
                    str(event.comment),
                    str(event.count),
                ])
            data = buffer.getvalue()

        response = HttpResponse(data, content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


@admin.register(CountAccessCode)
class CountAccessCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "description", "as_queue", "code_actions")
    actions = ("make_pdf",)

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
        return self.make_pdf(request, CountAccessCode.objects.filter(pk=object_id))

    def make_pdf(self, request, queryset):
        access_codes = queryset.all()

        if len(access_codes) == 1:
            filename = f"c3foc-counting-code-{access_codes[0]}.pdf"
        else:
            filename = f"c3foc-{len(access_codes)}-counting-codes.pdf"
        data = generate_access_code_pdf(request, access_codes, filename)

        response = HttpResponse(data, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
