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
    if not dt:
        return ''
    now = timezone.now()
    delta = now - dt

    seconds = delta.seconds
    days = delta.days
    hours = seconds / 3600
    minutes = seconds / 60

    suffix = " ago" if days >= 0 else ""
    prefix = "in " if days < 0 else ""

    if days > 0:
        if shorter:
            return f"{days:.1f}d"
        return f"{prefix}{days:.0f}d {hours:.0f}h{suffix}"
    elif hours >= 2:
        if shorter:
            return f"{hours:.0f}h"
        return f"{prefix}{hours:.0f}h{suffix}"
    elif minutes > 1:
        if shorter:
            return f"{minutes:.0f}m"
        return f"{prefix}{minutes:.0f} min{suffix}"
    else:
        return 'now'

register.filter('timesince_short', timesince_short)

def is_soon(dt, hours=1):
    if not dt: return False
    now = timezone.now()
    if hours < 0:
        delta = now - dt
        hours = -hours
    else:
        delta = dt - now
    return delta.days < 0 or (delta.days == 0 and delta.seconds < hours * 3600)

register.filter('is_soon', is_soon)

def seconds_to_duration(s):
    if not s:
        return ""
    if s > 3600:
        return f"{s/3600:.0f}h {s/60%60:.0f}m"
    return f"{s/60:.0f}m"

register.filter('seconds_to_duration', seconds_to_duration)
