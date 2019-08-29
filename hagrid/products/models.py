from django.contrib.auth.models import User
from django.db import models



class Product(models.Model):
    name = models.CharField(max_length=30, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name


class SizeGroup(models.Model):
    name = models.CharField(max_length=30, unique=True)
    
    def __str__(self):
        return self.name

class Size(models.Model):
    name = models.CharField(max_length=30)
    group = models.ForeignKey(SizeGroup, related_name='sizes', on_delete=models.CASCADE)

    def __str__(self):
        return "{} {}".format(str(self.group), self.name)


class Variation(models.Model):
    STATE_SUBMITTED = 'available'
    STATE_FEW_AVAILABLE = 'few available'
    STATE_SOLD_OUT = 'sold out'
    AVAILABILITY_STATES = [
            (STATE_SUBMITTED, 'many available'),
            (STATE_FEW_AVAILABLE, 'few available'),
            (STATE_SOLD_OUT, 'sold out')
    ]
    size = models.ForeignKey(Size, on_delete=models.CASCADE, related_name="variations")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    initial_amount = models.IntegerField(default=100)
    availability = models.CharField(default=AVAILABILITY_STATES[0], max_length=20, choices=AVAILABILITY_STATES)

    def __str__(self):
        return "{} ({})".format(str(self.product), str(self.size))


class AvailabilityEvent(models.Model):
    old_state = models.CharField(max_length=20, choices=Variation.AVAILABILITY_STATES)
    new_state = models.CharField(max_length=20, choices=Variation.AVAILABILITY_STATES)
    datetime = models.DateTimeField(auto_now=True)
    variation = models.ForeignKey(Variation, related_name='events', on_delete=models.CASCADE)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
