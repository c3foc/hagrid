import math
import secrets

from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django_eventstream import send_event
from positions import PositionField

from hagrid.operations.models import Event, EventTime


class StoreSettings(models.Model):
    dashboard_is_public = models.BooleanField(
        help_text="Show the dashboard to anonymous users", default=True
    )
    gallery_is_public = models.BooleanField(
        help_text="Show the gallery to anonymous users", default=True
    )
    reservations_enabled = models.BooleanField(
        help_text="Allow people to submit reservations", default=False
    )
    reservations_link_in_navbar = models.BooleanField(
        help_text="Show the link to the reservation form in the navbar", default=False
    )
    login_link_in_navbar = models.BooleanField(
        help_text="Show the link to the login page in the navbar", default=True
    )
    dashboard_text = models.TextField(
        help_text="HTML that will be rendered on the top of the dashboard",
        blank=True,
        default="",
    )
    reservation_faq_text = models.TextField(
        help_text="HTML that will be rendered reservation detail pages",
        blank=True,
        default="",
    )
    counting_enabled = models.BooleanField(
        help_text="Allow people with 'secret' URLs for counting items to record changes",
        default=False,
    )

    def __str__(self):
        return "The Store Settings"

    class Meta:
        verbose_name = "Store Settings"
        verbose_name_plural = "Store Settings"

    def save(self, *args, **kwargs):
        self.id = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass


class ProductCategory(models.Model):
    name = models.CharField(max_length=200, unique=True)
    position = PositionField()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["position"]


class Product(models.Model):
    name = models.CharField(max_length=250, unique=True)
    position = PositionField()
    category = models.ForeignKey(
        ProductCategory,
        related_name="products",
        on_delete=models.PROTECT,
    )
    size_scale = models.ForeignKey("SizeScale", on_delete=models.PROTECT, related_name="products")

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["position"]


class SizeScale(models.Model):
    name = models.CharField(max_length=60, unique=True)
    position = PositionField()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["position"]


class Size(models.Model):
    name = models.CharField(max_length=30, unique=True, blank=True)
    scale = models.ForeignKey(SizeScale, related_name="sizes", on_delete=models.CASCADE)
    position = PositionField(collection="scale")

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["position"]


class Design(models.Model):
    name = models.CharField(max_length=200)
    position = PositionField()
    event = models.ForeignKey(Event, related_name="designs", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.event!s} {self.name}"

    class Meta:
        ordering = ["position"]


class DesignVariation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="design_variations")
    design = models.ForeignKey(Design, on_delete=models.CASCADE, related_name="variations")

    def __str__(self):
        return f"{self.design!s} {self.product!s}"


class Price(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="prices")
    valid_at = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="sale_prices")
    valid_for_products_from_event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="historic_prices"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = (("product", "valid_for_products_from_event", "valid_at"),)

    def __str__(self):
        s = f"{self.valid_for_products_from_event!s} {self.product!s} at {self.valid_at!s}"
        if self.valid_for_products_from_event != self.valid_at:
            return f"old {s}"
        return s


class SizeVariation(models.Model):
    """
    A size variation is a concrete item
    """

    STATE_MANY_AVAILABLE = "available"
    STATE_FEW_AVAILABLE = "few available"
    STATE_SOLD_OUT = "sold out"
    AVAILABILITY_STATES = [
        (STATE_MANY_AVAILABLE, "available"),
        (STATE_FEW_AVAILABLE, "few available"),
        (STATE_SOLD_OUT, "sold out"),
    ]
    size = models.ForeignKey(Size, on_delete=models.CASCADE, related_name="variations")
    design_variation = models.ForeignKey(
        DesignVariation, on_delete=models.CASCADE, related_name="size_variations"
    )

    count = models.IntegerField(blank=True, null=True)
    counted_at = models.DateTimeField(blank=True, null=True)
    count_reserved_until = models.DateTimeField(blank=True, null=True)
    count_disabled_until = models.DateTimeField(blank=True, null=True)
    count_disabled_reason = models.CharField(max_length=30, blank=True, null=True)
    count_prio_bumped = models.BooleanField(default=False)

    availability = models.CharField(
        default=STATE_MANY_AVAILABLE, max_length=20, choices=AVAILABILITY_STATES
    )

    amount_initial = models.IntegerField(
        verbose_name="Amount received from the producer", blank=True, null=True
    )
    amount_preordered = models.IntegerField(
        verbose_name="Amount preordered from customers", blank=True, null=True
    )

    crate_size = models.IntegerField(
        help_text="How many items of this variation come in a crate?",
        blank=True,
        null=True,
    )

    def __str__(self):
        return f"{self.design_variation!s} {self.size!s}"

    @property
    def availability_progress(self):
        progress = 0
        if self.count is not None and self.amount_initial:
            progress = self.count / self.amount_initial * 100
        return f"{progress:.1f}%"

    @property
    def is_count_reserved(self):
        return self.count_reserved_until and self.count_reserved_until > timezone.now()

    @property
    def is_count_disabled(self):
        return self.count_disabled_until and self.count_disabled_until > timezone.now()

    @property
    def computed_availability(self):
        if self.count is None:
            return None

        if self.count == 0:
            return SizeVariation.STATE_SOLD_OUT

        if self.count <= 2 or (
            self.amount_initial is not None and self.count < self.amount_initial * 0.1
        ):
            return SizeVariation.STATE_FEW_AVAILABLE

        return SizeVariation.STATE_MANY_AVAILABLE

    def get_count_priority(self, event_time: EventTime):
        scores = {}
        info = {}

        def count_severity(count, amount_initial, exp=0.5):
            try:
                return max(0, 1 - math.pow(count / amount_initial, exp))
            except ArithmeticError:
                return 1

        if self.count_prio_bumped:
            scores["bumped"] = 1.0

        if self.count == 0:
            scores["depleted"] = 0
        elif not self.amount_initial:
            scores["invalid"] = 0
        else:
            now = event_time.datetime_to_event_time(timezone.now())

            if self.count is None or self.counted_at is None:
                # pretend we counted all items at t=0 with their amount_initial
                count = self.amount_initial
                count_event_time = 0
                # add a little score that indicates that don't really know much about this item's count
                # or sale rate
                scores["missing_count"] = 0.2
            else:
                count = self.count
                count_event_time = event_time.datetime_to_event_time(self.counted_at)

            # try to estimate the current count
            total_sold = self.amount_initial - count
            sale_rate = max(0, total_sold / max(1, count_event_time))
            estimate = self.amount_initial - now * sale_rate
            estimated_count = min(self.amount_initial, max(0, estimate))

            scores["running_low_estimated"] = count_severity(estimated_count, count)
            info["estimated_count"] = estimated_count
            info["sale_rate"] = sale_rate * 3600

            scores["running_low"] = 0.5 * count_severity(count, self.amount_initial)

            count_age = max(0, now - count_event_time)
            scores["outdated_count"] = 0.5 * math.pow(count_age / 3600 / 4.0, 0.5)
            info["count_age"] = count_age

            # Penalize recently counted items to push them to the end of the queue
            # Items counted within the last 4 hours get a negative score that fades over time
            if count_age < 4 * 3600:
                recently_counted_penalty = -1.0 * (1 - count_age / (4 * 3600))
                scores["recently_counted"] = recently_counted_penalty

        return {
            "scores": scores,
            "info": info,
            "total": sum(scores.values(), 0),
            "highest_reason": max(scores.items(), key=lambda s: s[1])[0],
        }

    @property
    def has_crate_size(self):
        return bool(self.crate_size)

    @property
    def crate_size_value(self):
        return self.crate_size or None


class AvailabilityEvent(models.Model):
    old_state = models.CharField(max_length=20, choices=SizeVariation.AVAILABILITY_STATES)
    new_state = models.CharField(max_length=20, choices=SizeVariation.AVAILABILITY_STATES)
    datetime = models.DateTimeField(auto_now=True)
    variation = models.ForeignKey(SizeVariation, related_name="events", on_delete=models.CASCADE)

    def __str__(self):
        return "At {} {} changed from {} to {}".format(
            self.datetime.strftime("%Y-%m-%d %H:%M:%S"),
            str(self.variation),
            self.old_state,
            self.new_state,
        )


class CountEvent(models.Model):
    count = models.IntegerField(blank=True, null=True)
    datetime = models.DateTimeField(auto_now=True)
    variation = models.ForeignKey(
        SizeVariation, related_name="count_events", on_delete=models.CASCADE
    )
    comment = models.TextField(blank=True, default="")
    name = models.TextField(blank=True, default="")

    def __str__(self):
        date = self.datetime.strftime("%Y-%m-%d %H:%M:%S")
        return f"At {date} {self.variation} changed to {self.count} available"


def generate_access_code():
    return secrets.token_urlsafe(12)


class CountAccessCode(models.Model):
    code = models.CharField(
        max_length=32,
        unique=True,
        default=generate_access_code,
        help_text="unique URL part, keep this (rather) secret",
    )

    name = models.CharField(
        max_length=32,
        unique=False,
        blank=True,
        null=True,
        help_text="A name to identify or describe this code to admins (only shown there)",
    )

    # filters
    products = models.ManyToManyField(
        Product, help_text="allow editing only variations these products", blank=True
    )
    events = models.ManyToManyField(
        Event,
        help_text="allow editing only products from these events",
        blank=True,
    )
    sizes = models.ManyToManyField(
        Size, help_text="allow editing only variations these sizes", blank=True
    )

    disabled = models.BooleanField(help_text="disable the code so it cannot be used at the moment")
    as_queue = models.BooleanField(help_text="use queue mode for this code", default=False)

    def __str__(self):
        filters = []
        for attr in ["products", "SizeScales", "sizes"]:
            items = getattr(self, attr).all()

            if items:
                filters.append("/".join(str(i) for i in items))

        filters = ", ".join(filters) if filters else "everything"

        return f"Access code for {filters}"

    def get_absolute_url(self):
        return reverse("variation_count", kwargs={"code": self.code})

    @property
    def variations(self):
        queryset = SizeVariation.objects

        products = self.products.all()
        if products:
            queryset = queryset.filter(product__in=products)

        sizes = self.sizes.all()
        if sizes:
            queryset = queryset.filter(size__in=sizes)

        SizeScales = self.SizeScales.all()
        if SizeScales:
            queryset = queryset.filter(size__group__in=SizeScales)

        queryset = queryset.order_by(
            "product__product_group__position",
            "product__position",
            "size__group__position",
            "size__position",
        )

        return queryset


@receiver(pre_save, sender=SizeVariation, dispatch_uid="variation_availability_change")
def variation_availability_change(sender, instance, **kwargs):
    new_instance = instance
    try:
        old_instance = SizeVariation.objects.get(pk=instance.pk)
    except SizeVariation.DoesNotExist:
        return

    if new_instance.availability != old_instance.availability:
        AvailabilityEvent(
            old_state=old_instance.availability,
            new_state=new_instance.availability,
            variation=instance,
        ).save()
        send_event(
            "availability-display",
            f"variation-{instance.id}",
            data=render_to_string(
                "dashboard/product_availability_tag.html",
                {
                    "variation": instance,
                },
            ),
            json_encode=False,
        )
        # Availbility change form
        from hagrid.products.views.config import VariationsAvailabilityForm

        form = VariationsAvailabilityForm([instance])
        field = form.field_for_rendering_by_variation(instance)
        send_event(
            "availability-form",
            f"variation-{instance.id}",
            data=render_to_string(
                "operator/variation_availability_box.html",
                {
                    "field": field,
                    "variation": instance,
                },
            ),
            json_encode=False,
        )
