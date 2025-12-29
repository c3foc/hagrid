from django.db import models

import markdown

class StaticPage(models.Model):
    slug = models.SlugField(max_length=200, db_index=True, unique=True)
    title = models.CharField(max_length=200)
    content = models.TextField(default="", blank=True)
    show_in_footer = models.BooleanField(default=False, db_index=True)
    show_in_header = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def content_rendered(self):
        return mark_safe(markdown.markdown(self.content))

    def __str__(self):
        return self.title

def image_upload_path(instance, filename):
    return "pageimages/{}/{}".format(instance.page.slug, filename)

class PageImage(models.Model):
    page = models.ForeignKey(
        StaticPage, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to=image_upload_path)
    caption = models.CharField(max_length=200, blank=True)
    alt_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.page.title} - {self.image.filename}"
