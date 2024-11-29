from datetime import timedelta, datetime, timezone
from django.utils import timezone
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

def timesince_short(dt, shorter=False):
    now = timezone.now()
    delta = now - dt

    seconds = delta.seconds
    days = delta.days
    hours = seconds / 3600
    minutes = seconds / 60

    if days > 0:
        if shorter:
            return f"{days:.1f}d"
        return f"{days:.0f}d {hours:.0f}h ago"
    elif hours >= 2:
        if shorter:
            return f"{hours:.0f}h"
        return f"{hours:.0f}h ago"
    elif minutes > 1:
        if shorter:
            return f"{minutes:.0f}m"
        return f"{minutes:.0f} min ago"
    else:
        return 'now'



register.filter('timesince_short', timesince_short)
