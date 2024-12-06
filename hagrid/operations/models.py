from django.utils.translation import gettext_lazy as _
from datetime import datetime

import numpy
from django.db import models


class OpenStatus(models.Model):
    class Mode(models.TextChoices):
        CLOSED = "closed", _("Closed")
        OPEN = "open", _("Open")
        PRESALE_PICKUP = "presale", _("Presale pickup")

    datetime = models.DateTimeField(default=datetime.now)
    comment = models.TextField(
        help_text="information about this operating time", blank=True, null=True
    )
    public_info = models.CharField(
        help_text="shown on dashboard",
        max_length=100,
        blank=True,
        null=True,
        default=None,
    )
    mode = models.CharField(
        max_length=7,
        choices=Mode.choices,
        default=Mode.CLOSED
    )

    class Meta:
        verbose_name_plural = "open statuses"
        ordering = ['datetime']

    def __str__(self):
        date = self.datetime.strftime("%Y-%m-%d %H:%M:%S")
        status = "open" if self.open else "closed"
        return f"{status} at {date}"

    @property
    def open(self):
        return self.mode != OpenStatus.Mode.CLOSED

    @classmethod
    def get_status(cls):
        now = datetime.now()

        prev_status = cls.objects.filter(datetime__lt=now).order_by("-datetime").first()
        next_status = cls.objects.filter(datetime__gte=now).order_by("datetime").first()

        is_open = prev_status.open if prev_status else False

        return {
            "open": is_open,
            "start": prev_status.datetime if prev_status else None,
            "stop": next_status.datetime if next_status else None,
            "closed_info": prev_status.public_info
            if not is_open
            else (next_status.public_info if next_status else None),
            "open_info": prev_status.public_info
            if is_open
            else (next_status.public_info if next_status else None),
        }

    @classmethod
    def make_datetime_to_event_time(cls):
        statuses = cls.objects.order_by("datetime").all()
        times = numpy.array([int(status.datetime.timestamp()) for status in statuses])
        opens = numpy.array([1 if status.mode == OpenStatus.Mode.OPEN else 0 for status in statuses])
        timediffs = numpy.diff(times, prepend=[times[0]])
        opendiffs = numpy.where(opens, 0, timediffs)
        openings = numpy.cumsum(opendiffs)

        def result(dt: datetime | int | float):
            if isinstance(dt, datetime):
                dt = dt.timestamp()

            idx = numpy.searchsorted(times, dt) - 1
            prev_time = times[idx]
            eventhour = openings[idx]
            if opens[idx]:
                eventhour += dt - prev_time
            return float(eventhour)

        return result
