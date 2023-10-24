from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from django.urls import reverse

from .utils import generate_date_based_reference_code


class Report(models.Model):
    code = models.CharField(
        max_length=17,
        editable=False,
        unique=True,
        default=generate_date_based_reference_code,
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.BigIntegerField()
    content_object = GenericForeignKey()
    message = models.TextField(
        max_length=5000,
        help_text="Describe the issue with the content or account.",
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return str(self.code)

    def get_absolute_url(self):
        return reverse("moderation:report", kwargs={"code": self.code})


class Response(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE)
    message = models.TextField(max_length=5000)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created"]
