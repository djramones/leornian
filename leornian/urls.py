"""URL configuration for leornian project."""

from django.contrib import admin
from django.urls import path


admin.site.site_header = admin.site.site_title = "Leornian admin"

urlpatterns = [
    path("admin/", admin.site.urls),
]
