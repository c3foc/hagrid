from .models import (
    Product,
    Size,
    SizeGroup,
    Variation,
)


class SizeTable:
    def __init__(
        self,
        sizegroup,
        render_variation=None,
        render_empty=None,
        show_empty_rows=False,
        products_queryset=None,
    ):
        self.sizegroup = sizegroup
        self.show_empty_rows = show_empty_rows
        if not render_variation:
            render_variation = lambda v: v.availability
        self.render_variation = render_variation
        if not render_empty:
            render_empty = lambda p, s: ""
        self.render_empty = render_empty
        self.products_queryset = (
            products_queryset
            if products_queryset is not None
            else Product.objects.all()
        )
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

        for product in self.products_queryset:
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
