from django.db import models
from datetime import datetime


class OpenStatus(models.Model):
    datetime = models.DateTimeField(default=datetime.now)
    open = models.BooleanField(help_text="whether we're open or closed", default=False)
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

    class Meta:
        verbose_name_plural = "open statuses"

    def __str__(self):
        date = self.datetime.strftime("%Y-%m-%d %H:%M:%S")
        status = "open" if self.open else "closed"
        return f"{status} at {date}"

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
            if not open
            else (next_status.public_info if next_status else None),
            "open_info": prev_status.public_info
            if open
            else (next_status.public_info if next_status else None),
        }
