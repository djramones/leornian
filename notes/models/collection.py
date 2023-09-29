from django.db import models
from django.conf import settings
from django.utils import timezone


class Collection(models.Model):
    note = models.ForeignKey("Note", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    last_drilled = models.DateTimeField(default=timezone.now)
    promoted = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["note", "user"], name="unique_collect"),
        ]
