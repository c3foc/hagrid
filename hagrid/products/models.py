import secrets

from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from positions import PositionField

class StoreSettings(models.Model):
    dashboard_is_public = models.BooleanField(help_text="Show the dashboard to anonymous users", default=True)
    gallery_is_public = models.BooleanField(help_text="Show the gallery to anonymous users", default=True)
    reservations_enabled = models.BooleanField(help_text="Allow people to submit reservations", default=False)
    reservations_link_in_navbar = models.BooleanField(help_text="Show the link to the reservation form in the navbar", default=False)
    login_link_in_navbar = models.BooleanField(help_text="Show the link to the login page in the navbar", default=True)
    dashboard_text = models.TextField(help_text="HTML that will be rendered on the top of the dashboard", blank=True, default="")
    reservation_faq_text = models.TextField(help_text="HTML that will be rendered reservation detail pages", blank=True, default="")

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
    availability = models.CharField(default=STATE_MANY_AVAILABLE, max_length=20, choices=AVAILABILITY_STATES)

    def __str__(self):
        return "{} ({})".format(str(self.product), str(self.size))


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

    # filters
    products = models.ManyToManyField(Product, help_text="allow editing only variations these products", blank=True)
    sizegroups = models.ManyToManyField(SizeGroup, help_text="allow editing only variations these sizegroups", blank=True)
    sizes = models.ManyToManyField(Size, help_text="allow editing only variations these sizes", blank=True)

    disabled = models.BooleanField(help_text="disable the code so it cannot be used at the moment")

    def __str__(self):
        filters = []
        for attr in ['products', 'sizegroups', 'sizes']:
            items = getattr(self, attr).all()

            if items:
                filters.append("/".join(str(i) for i in items))

        filters = ", ".join(filters) if filters else "everything"

        return f"Access code for {filters}"

    def get_absolute_url(self):
        print("CODE", self.code)
        return reverse('variationcount', kwargs={'code':self.code})

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
