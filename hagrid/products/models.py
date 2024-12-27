from datetime import datetime
from math import log
import math
import secrets
from typing import Iterator

from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from django.utils import timezone
from positions import PositionField

from hagrid.operations.models import EventTime

class StoreSettings(models.Model):
    dashboard_is_public = models.BooleanField(help_text="Show the dashboard to anonymous users", default=True)
    gallery_is_public = models.BooleanField(help_text="Show the gallery to anonymous users", default=True)
    reservations_enabled = models.BooleanField(help_text="Allow people to submit reservations", default=False)
    reservations_link_in_navbar = models.BooleanField(help_text="Show the link to the reservation form in the navbar", default=False)
    login_link_in_navbar = models.BooleanField(help_text="Show the link to the login page in the navbar", default=True)
    dashboard_text = models.TextField(help_text="HTML that will be rendered on the top of the dashboard", blank=True, default="")
    reservation_faq_text = models.TextField(help_text="HTML that will be rendered reservation detail pages", blank=True, default="")
    counting_enabled = models.BooleanField(help_text="Allow people with 'secret' URLs for counting items to record changes", default=False)

    def __str__(self):
        return "The Store Settings"

    class Meta:
        verbose_name = "Store Settings"
        verbose_name_plural = "Store Settings"

    def save(self, *args, **kwargs):
        self.id=1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

class ProductGroup(models.Model):
    name = models.CharField(max_length=30, unique=True)
    description = models.TextField(help_text="HTML that will be rendered in the dashboard section", blank=True, default="")
    position = PositionField()
    display_in_dashboard = models.BooleanField(help_text="Show the group in the dashboard", default=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['position']


class Product(models.Model):
    name = models.CharField(max_length=30, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    position = PositionField()
    product_group = models.ForeignKey(ProductGroup, related_name='products', on_delete=models.SET_NULL, default=None, blank=True, null=True)
    crate_size = models.IntegerField(help_text="How many items of this product come in a crate?", blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['position']

class SizeGroup(models.Model):
    name = models.CharField(max_length=30, unique=True)
    position = PositionField()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['position']


class Size(models.Model):
    name = models.CharField(max_length=30)
    group = models.ForeignKey(SizeGroup, related_name='sizes', on_delete=models.CASCADE)
    position = PositionField(collection='group')

    def __str__(self):
        return "{} {}".format(str(self.group), self.name)

    class Meta:
        ordering = ['position']


class Variation(models.Model):
    STATE_MANY_AVAILABLE = 'available'
    STATE_FEW_AVAILABLE = 'few available'
    STATE_SOLD_OUT = 'sold out'
    AVAILABILITY_STATES = [
            (STATE_MANY_AVAILABLE, 'many available'),
            (STATE_FEW_AVAILABLE, 'few available'),
            (STATE_SOLD_OUT, 'sold out')
    ]
    size = models.ForeignKey(Size, on_delete=models.CASCADE, related_name="variations")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variations")
    initial_amount = models.IntegerField(default=100)
    count = models.IntegerField(blank=True, null=True)
    counted_at = models.DateTimeField(blank=True, null=True)
    count_reserved_until = models.DateTimeField(blank=True, null=True)
    count_disabled_until = models.DateTimeField(blank=True, null=True)
    count_disabled_reason = models.CharField(max_length=30, blank=True, null=True)
    count_prio_bumped = models.BooleanField(default=False)
    availability = models.CharField(default=STATE_MANY_AVAILABLE, max_length=20, choices=AVAILABILITY_STATES)
    crate_size = models.IntegerField(help_text="How many items of this variation come in a crate (overrides product setting)?", blank=True, null=True)

    def __str__(self):
        return "{} ({})".format(str(self.product), str(self.size))

    @property
    def availability_progress(self):
        progress = 0
        if self.count is not None and self.initial_amount:
            progress = self.count / self.initial_amount * 100
        return f"{progress:.1f}%"

    @property
    def is_count_reserved(self):
        return self.count_reserved_until and self.count_reserved_until > timezone.now()

    @property
    def is_count_disabled(self):
        return self.count_disabled_until and self.count_disabled_until > timezone.now()

    @property
    def computed_availability(self):
        if self.count is not None and self.initial_amount:
            if self.count == 0:
                return Variation.STATE_SOLD_OUT

            if self.count <= 2 or self.count < self.initial_amount * 0.1:
                return Variation.STATE_FEW_AVAILABLE

            return Variation.STATE_MANY_AVAILABLE

        return None

    def get_count_priority(self, event_time: EventTime):
        scores = {}
        info = {}

        def count_severity(count, initial_amount, exp=0.5):
            try:
                return max(0, 1 - math.pow(count / initial_amount, exp))
            except ArithmeticError:
                return 1

        if self.count_prio_bumped:
            scores['bumped'] = 1.0

        if self.count == 0:
            scores['depleted'] = 0
        elif not self.initial_amount:
            scores['invalid'] = 0
        else:
            now = event_time.datetime_to_event_time(datetime.now())

            if self.count is None or self.counted_at is None:
                # pretend we counted all items at t=0 with their initial_amount
                count = self.initial_amount
                count_event_time = 0
                # add a little score that indicates that don't really know much about this item's count
                # or sale rate
                scores['missing_count'] = 0.2
            else:
                count = self.count
                count_event_time = event_time.datetime_to_event_time(self.counted_at)

            # try to estimate the current count
            total_sold = self.initial_amount - count
            sale_rate = max(0, total_sold / max(1, count_event_time))
            estimate = self.initial_amount - now * sale_rate
            estimated_count = min(self.initial_amount, max(0, estimate))

            scores['running_low_estimated'] = count_severity(estimated_count, count)
            info['estimated_count'] = estimated_count
            info['sale_rate'] = sale_rate * 3600

            scores['running_low'] = 0.5 * count_severity(count, self.initial_amount)

            count_age = max(0, now - count_event_time)
            scores['outdated_count'] = 0.5 * math.pow(count_age / 3600 / 4.0, 0.5)
            info['count_age'] = count_age

        return {
            'scores': scores,
            'info': info,
            'total': sum(scores.values(), 0),
            'highest_reason': max(scores.items(), key=lambda s:s[1])[0],
        }

    @property
    def has_crate_size(self):
        return self.product.crate_size is not None if (self.crate_size is None) else (self.crate_size != 0)


    @property
    def crate_size_value(self):
        return self.product.crate_size if self.crate_size is None else None if self.crate_size == 0 else self.crate_size

class VariationAvailabilityEvent(models.Model):
    old_state = models.CharField(max_length=20, choices=Variation.AVAILABILITY_STATES)
    new_state = models.CharField(max_length=20, choices=Variation.AVAILABILITY_STATES)
    datetime = models.DateTimeField(auto_now=True)
    variation = models.ForeignKey(Variation, related_name='events', on_delete=models.CASCADE)

    def __str__(self):
        return "At {} {} changed from {} to {}".format(
                self.datetime.strftime('%Y-%m-%d %H:%M:%S'),
                str(self.variation),
                self.old_state,
                self.new_state
        )

class VariationCountEvent(models.Model):
    count = models.IntegerField(blank=True, null=True)
    datetime = models.DateTimeField(auto_now=True)
    variation = models.ForeignKey(Variation, related_name='count_events', on_delete=models.CASCADE)
    comment = models.TextField(blank=True, default="")
    name = models.TextField(blank=True, default="")

    def __str__(self):
        date = self.datetime.strftime('%Y-%m-%d %H:%M:%S')
        return f"At {date} {self.variation} changed to {self.count} available"

def generate_access_code():
    return secrets.token_urlsafe(12)

class VariationCountAccessCode(models.Model):
    code = models.CharField(max_length=32, unique=True, default=generate_access_code,
                            help_text="unique URL part, keep this (rather) secret")

    name = models.CharField(max_length=32, unique=False, blank=True, null=True,
                            help_text="A name to identify or describe this code to admins (only shown there)")

    # filters
    products = models.ManyToManyField(Product, help_text="allow editing only variations these products", blank=True)
    sizegroups = models.ManyToManyField(SizeGroup, help_text="allow editing only variations these sizegroups", blank=True)
    sizes = models.ManyToManyField(Size, help_text="allow editing only variations these sizes", blank=True)

    disabled = models.BooleanField(help_text="disable the code so it cannot be used at the moment")
    as_queue = models.BooleanField(help_text="use queue mode for this code", default=False)

    def __str__(self):
        filters = []
        for attr in ['products', 'sizegroups', 'sizes']:
            items = getattr(self, attr).all()

            if items:
                filters.append("/".join(str(i) for i in items))

        filters = ", ".join(filters) if filters else "everything"

        return f"Access code for {filters}"

    def get_absolute_url(self):
        return reverse('variation_count', kwargs={'code':self.code})

    @property
    def variations(self):
        queryset = Variation.objects

        products = self.products.all()
        if products:
            queryset = queryset.filter(product__in=products)

        sizes = self.sizes.all()
        if sizes:
            queryset = queryset.filter(size__in=sizes)

        sizegroups = self.sizegroups.all()
        if sizegroups:
            queryset = queryset.filter(size__group__in=sizegroups)

        queryset = queryset.order_by(
            "product__product_group__position",
            "product__position",
            "size__group__position",
            "size__position",
        )

        return queryset

from django.db.models.signals import pre_save
from django.dispatch import receiver


@receiver(pre_save, sender=Variation, dispatch_uid="variation_availability_change")
def variation_availability_change(sender, instance,  **kwargs):
    new_instance = instance
    try:
        old_instance = Variation.objects.get(pk=instance.pk)
    except Variation.DoesNotExist:
        return

    if new_instance.availability != old_instance.availability:
        VariationAvailabilityEvent(
            old_state=old_instance.availability,
            new_state=new_instance.availability,
            variation=instance
        ).save()
