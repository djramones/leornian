from django.contrib import admin
from django.conf import settings

from .models import Note


if settings.DEBUG:
    admin.site.register(Note)
