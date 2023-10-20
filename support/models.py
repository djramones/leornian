import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, blank=True, null=True, on_delete=models.SET_NULL
    )
    to_email = models.EmailField(blank=True)
    subject = models.CharField(max_length=78)
    message = models.TextField(max_length=5000)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def get_absolute_url(self):
        return reverse("support:message-detail", kwargs={"pk": self.pk})
