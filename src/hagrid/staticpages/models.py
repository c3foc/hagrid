import markdown
from django.db import models
from django.utils.safestring import mark_safe


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
