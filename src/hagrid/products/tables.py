from .models import (
    DesignVariation,
    Product,
    SizeVariation,
)


class SizeTable:
    def __init__(
        self,
        SizeScale,
        render_variation=None,
        render_empty=None,
        show_empty_rows=False,
        products_queryset=None,
    ):
        self.SizeScale = SizeScale
        self.show_empty_rows = show_empty_rows
        if not render_variation:
            render_variation = lambda v: v.availability
        self.render_variation = render_variation
        if not render_empty:
            render_empty = lambda p, s: ""
        self.render_empty = render_empty
        self.products_queryset = (
            products_queryset if products_queryset is not None else Product.objects.all()
        )
        self.entries = self.generate_entries()

    @property
    def header(self):
        return [self.SizeScale.name] + [size.name for size in self.SizeScale.sizes.all()]

    def generate_entries(self):
        rows = []
        all_variations = SizeVariation.objects.all()
        bool(all_variations)  # cache all variations in queryset
        SizeScale_sizes = self.SizeScale.sizes.all()

        for product in self.products_queryset:
            row = [product.name]
            found_variation = False
            for size in SizeScale_sizes:
                try:
                    variation = all_variations.get(product=product, size=size)
                    row.append(self.render_variation(variation))
                    found_variation = True
                except SizeVariation.DoesNotExist:
                    row.append(self.render_empty(product, size))
            if found_variation or self.show_empty_rows:
                rows.append(row)
        return rows


class ProductTable:
    def __init__(
        self,
        title,
        product,
        only_events_in=None,
        render_variation=None,
        render_empty=None,
        show_empty_rows=False,
        table_class: str = "",
    ):
        self.title = title
        self.product = product
        self.only_events_in = only_events_in
        self.table_class = table_class
        self.show_empty_rows = show_empty_rows
        self.render_variation = render_variation or (lambda v: v.availability)
        self.render_empty = render_empty or (lambda *_args: "")

        self.rows = list(self.generate_rows())

    def generate_rows(self):
        design_variations = DesignVariation.objects.filter(
            product=self.product,
        )
        if self.only_events_in:
            design_variations = design_variations.filter(design__event__in=self.only_events_in)
        bool(design_variations)
        sizes = self.product.size_scale.sizes.all()
        bool(sizes)

        all_variations = {
            (v.design_variation_id, v.size_id): v
            for v in SizeVariation.objects.filter(design_variation__in=design_variations)
        }

        for design_variation in design_variations:
            row = {
                "design_variation": design_variation,
                "variations": [],
            }
            found_variation = False
            for size in sizes:
                try:
                    variation = all_variations[(design_variation.id, size.id)]
                    row["variations"].append({
                        "size": size,
                        "variation": variation,
                        "html": self.render_variation(variation),
                    })
                    found_variation = True
                except KeyError:
                    row["variations"].append({
                        "size": size,
                        "variation": None,
                        "html": self.render_empty(design_variation, size),
                    })
            if found_variation or self.show_empty_rows:
                yield row

    @property
    def column_width(self):
        return "200"
        # return f"{100/(self.column_count + 1):.1f}%"
