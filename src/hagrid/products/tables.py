from .models import (
    DesignVariation,
    SizeVariation,
)


class ProductTable:
    """
    A table where the rows are design variants of a product
    and the columns sizes of the associated size scale.
    Can be limited to designs of specific events.
    """

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
        if self.only_events_in is not None:
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
