from PIL.Image import Resampling
from django.contrib.auth.models import User
from django.db import models
from PIL import Image

from hagrid.products.models import Variation


class GalleryImage(models.Model):
    image = models.ImageField(upload_to="galleryimages/")
    variation = models.ForeignKey(Variation, blank=True, null=True, on_delete=models.SET_NULL)
    title = models.CharField(max_length=100, blank=True)
    caption = models.TextField(blank=True)
    alt_text = models.TextField(blank=True)

    def __str__(self):
        return "{} {}".format(self.title, str(self.variation))

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.image:
            return

        # Resize image
        image = Image.open(str(self.image.path))
        w, h = image.size
        while w * h > 2 * 10**6:
            w, h = w // 2, h // 2
        image = image.resize((w, h), Resampling.NEAREST)
        image.save(str(self.image.path), 'PNG')

