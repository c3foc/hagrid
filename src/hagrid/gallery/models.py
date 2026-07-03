import secrets

from django.core.files.storage import storages
from django.db import models
from django.utils.text import slugify
from PIL import Image
from PIL.Image import Resampling

from hagrid.products.models import DesignVariation


def public_media_storage():
    return storages["public_media"]


def gallery_image_directory_path(instance, filename):
    random_path = secrets.token_urlsafe(8)
    slug = slugify(str(instance.design_variation))
    return f"galleryimages/{random_path}/{slug}_{filename}"


class GalleryImage(models.Model):
    image = models.ImageField(
        # file will be uploaded to PUBLIC_MEDIA_ROOT/<random>/<slug>_<filename>
        storage=public_media_storage(),
        upload_to=gallery_image_directory_path,
    )
    design_variation = models.ForeignKey(
        DesignVariation,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="images",
    )
    title = models.CharField(max_length=200, blank=True)
    caption = models.TextField(blank=True)
    alt_text = models.TextField(blank=True)

    def __str__(self):
        return self.title or str(self.design_variation)

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
        image.save(str(self.image.path), "PNG")
