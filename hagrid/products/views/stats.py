import math
from datetime import datetime
from typing import Iterable

import numpy
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_GET

from hagrid.operations.models import EventTime
from hagrid.products.models import Variation

MAX_FIT_DEGREE = 2


@login_required()
@require_GET
def operator_stats(request):
    event_time = EventTime()

    coefficients = numpy.zeros((MAX_FIT_DEGREE + 1,))
    for variation in Variation.objects.prefetch_related("count_events").all():
        xy = {}
        for c in variation.count_events.all():
            xy[event_time.datetime_to_event_time(c.datetime)] = c.count

        # pretend full sale at end of event if we never counted
        if not xy:
            xy[event_time.total_event_duration] = 0

        # track start value
        xy[0] = variation.initial_amount

        xy = numpy.array(sorted(xy.items()))

        degree = min(MAX_FIT_DEGREE, xy.shape[0] - 1)
        poly = numpy.polynomial.Polynomial.fit(xy[:, 0], xy[:, 1], degree)
        coefficients[: degree + 1] += poly.convert().coef

    @numpy.vectorize
    def get_stock_at(x):
        return sum(c * pow(x, i) for i, c in enumerate(coefficients))

    # Calculate the derivative (rate of change) of the stock polynomial
    # This gives us the sales rate directly
    @numpy.vectorize
    def get_sale_rate_at(x):
        # Derivative of polynomial: d/dx (c0 + c1*x + c2*x^2) = c1 + 2*c2*x
        return -sum(i * c * pow(x, i - 1) for i, c in enumerate(coefficients) if i > 0)

    INTERVAL = 300
    STEPS = math.ceil(event_time.total_event_duration / INTERVAL)
    stock_times = numpy.arange(STEPS) * INTERVAL
    if len(stock_times) > 0:
        stock = get_stock_at(stock_times)
    else:
        stock = numpy.array([])

    INTERVAL = 3600
    STEPS = math.ceil(event_time.total_event_duration / INTERVAL)
    rate_times = numpy.arange(STEPS) * INTERVAL
    if len(rate_times) > 0:
        # Use the derivative to get the instantaneous rate (items per second)
        # Then convert to items per hour by multiplying by 3600
        rate_per_second = get_sale_rate_at(rate_times)
        rate = rate_per_second * 3600  # Convert to items per hour
    else:
        rate = numpy.array([])

    availabilities = []
    for i, variation in enumerate(Variation.objects.prefetch_related("events").all()):
        xy = {0: 2}
        for c in variation.events.all():
            xy[event_time.datetime_to_event_time(c.datetime)] = (
                2
                if c.new_state == Variation.STATE_MANY_AVAILABLE
                else 1
                if c.new_state == Variation.STATE_FEW_AVAILABLE
                else 0
            )
        avail = sorted(xy.items())
        avail.append((event_time.total_event_duration, avail[-1][1]))
        timeline = [
            {"x": x, "x2": x2, "y": i, "v": v} for (x, v), (x2, _) in pairs(avail)
        ]

        availabilities.append({"variation": str(variation), "timeline": timeline})

    return render(
        request,
        "stats.html",
        {
            "chart_data": {
                "now": event_time.datetime_to_event_time(datetime.now()),
                "remainingStock": numpy.stack([stock_times, stock], axis=-1).tolist(),
                "saleRate": rate.tolist(),
                "downtimes": event_time.downtimes.tolist(),
                "availabilities": availabilities,
            },
        },
    )


def pairs(it):
    """Iterate over pairs (tuples of consecutive items, overlapping) from the
    original iterator.
    """
    i = iter(it)
    try:
        prev = next(i)
        while True:
            cur = next(i)
            yield prev, cur
            prev = cur
    except StopIteration:
        pass
