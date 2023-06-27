"""URL configuration for leornian project."""

from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView


admin.site.site_header = admin.site.site_title = "Leornian admin"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
]
