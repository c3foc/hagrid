from django.contrib.auth.models import User
from django.db import models
from positions import PositionField

class StoreSettings(models.Model):
    dashboard_is_public = models.BooleanField(help_text="Show the dashboard to anonymous users", default=True)
    gallery_is_public = models.BooleanField(help_text="Show the gallery to anonymous users", default=True)
    reservations_enabled = models.BooleanField(help_text="Allow people to submit reservations", default=False)
    reservations_link_in_navbar = models.BooleanField(help_text="Show the link to the reservation form in the navbar", default=False)
    login_link_in_navbar = models.BooleanField(help_text="Show the link to the login page in the navbar", default=True)
    dashboard_text = models.TextField(help_text="HTML that will be rendered on the top of the dashboard", blank=True, default="")

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


class Product(models.Model):
    name = models.CharField(max_length=30, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    position = PositionField()

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
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    initial_amount = models.IntegerField(default=100)
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


from django.db.models.signals import pre_save
from django.dispatch import receiver


@receiver(pre_save, sender=Variation, dispatch_uid="my_unique_identifier")
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
