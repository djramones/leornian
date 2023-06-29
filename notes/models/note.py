from django.db import models
from django.conf import settings
from django.utils import safestring
from django.urls import reverse

from markdown_it import MarkdownIt

from notes.utils import generate_reference_code


class Note(models.Model):
    class Visibility(models.IntegerChoices):
        NORMAL = 1
        UNLISTED = 2

    code = models.CharField(
        max_length=9, editable=False, unique=True, default=generate_reference_code
    )
    text = models.TextField(max_length=1200)
    visibility = models.PositiveSmallIntegerField(
        choices=Visibility.choices, default=Visibility.NORMAL
    )
    is_curated = models.BooleanField(default=False)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, blank=True, null=True, on_delete=models.SET_NULL
    )
    created = models.DateTimeField(auto_now_add=True)

    @property
    def html(self):
        """Render safe HTML from the Markdown-formatted `text` field."""
        return safestring.mark_safe(MarkdownIt("js-default").render(self.text))

    def __str__(self):
        return str(self.code)

    def get_absolute_url(self):
        return reverse("notes:single-note", kwargs={"slug": self.code})