from django.utils.translation import gettext_lazy as _
from datetime import datetime

import numpy
from django.db import models


class EventTime:
    total_event_duration: float

    def __init__(self):
        # TODO: make this more resilient against partial configuration or misconfiguration
        statuses = OpenStatus.objects.order_by("datetime").all()

        self.status_change_timestamps = numpy.array(
            [int(status.datetime.timestamp()) for status in statuses]
        )
        self.open_state_by_index = numpy.array(
            [1 if status.mode == OpenStatus.Mode.OPEN else 0 for status in statuses]
        )

        # time of each timestamp since the previous
        if len(self.status_change_timestamps):
            diffs = numpy.diff(
                self.status_change_timestamps,
                prepend=[self.status_change_timestamps[0]],
            )
        else:
            diffs = numpy.array([])

        # only the time of each timestamp since the previous IF that timespan was open
        opendiffs = numpy.where(self.open_state_by_index, 0, diffs)

        # cumulative sum adds to the time since the start of the event for open timesapns
        self.start_event_time_by_index = numpy.cumsum(opendiffs)

        self.downtimes = self.start_event_time_by_index[
            self.open_state_by_index.astype(numpy.bool)
        ]

        self.total_event_duration = (
            float(self.start_event_time_by_index[-1])
            if len(self.start_event_time_by_index)
            else 0
        )

    def datetime_to_event_time(self, dt: datetime | int | float) -> float:
        if isinstance(dt, datetime):
            dt = dt.timestamp()

        # Find the index of the previous status change timestamp
        idx = numpy.searchsorted(self.status_change_timestamps, dt) - 1

        # If the insert index is 0 then the event is before the first opening
        # and the event time is clipped to 0.
        if idx < 0:
            return 0

        # Find the event time for the previous status change
        start_event_time = self.start_event_time_by_index[idx]

        # Only add the time since the last change event if that event was an
        # "open" event, i.e. if the time since then counts as event time.
        if self.open_state_by_index[idx]:
            start_timestamp = self.status_change_timestamps[idx]
            event_time = start_event_time + (dt - start_timestamp)
        else:
            event_time = start_event_time

        # convert from numpy.float
        return float(event_time)


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
    mode = models.CharField(max_length=7, choices=Mode.choices, default=Mode.CLOSED)

    class Meta:
        verbose_name_plural = "open statuses"
        ordering = ["datetime"]

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
