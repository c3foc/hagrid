from django import template

from hagrid.products.models import Variation

register = template.Library()


def availability_class(availability):
    if availability == Variation.STATE_MANY_AVAILABLE: 
        return 'green'
    elif availability == Variation.STATE_FEW_AVAILABLE: 
        return 'yellow'
    elif availability == Variation.STATE_SOLD_OUT: 
        return 'red'
    else:
        return 'gray'


register.filter('availability_class', availability_class)
