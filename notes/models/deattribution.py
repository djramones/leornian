"""
Note deattribution (authorship removal) record.

Changes to instances of this model might need to be performed
within atomic transactions to ensure consistency.
"""

from django.db import models
from django.conf import settings


class Deattribution(models.Model):
    note = models.OneToOneField("Note", on_delete=models.CASCADE, primary_key=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]
