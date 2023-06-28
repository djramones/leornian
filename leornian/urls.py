"""URL configuration for leornian project."""

from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

from django.conf import settings

from . import views as site_views


admin.site.site_header = admin.site.site_title = "Leornian admin"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
]

if settings.DEBUG:
    urlpatterns.append(path("__debug__/", include("debug_toolbar.urls")))
    urlpatterns.append(path("__msgs__/", site_views.messages_test))
