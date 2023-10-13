"""URL configuration for leornian project."""

from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import path, include
from django.views.generic import TemplateView

from django.conf import settings

from . import views as site_views


admin.site.site_header = admin.site.site_title = "Leornian admin"

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        # django-registration override
        "accounts/register/",
        site_views.RegistrationView.as_view(),
        name="leornian-register",
    ),
    path("accounts/", include("django_registration.backends.activation.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path(
        "accounts/me/",
        login_required(TemplateView.as_view(template_name="my-account.html")),
        name="my-account",
    ),
    path("", include("notes.urls")),
    path("", site_views.home, name="home"),
]

if settings.DEBUG:
    urlpatterns.insert(0, path("__debug__/", include("debug_toolbar.urls")))
    urlpatterns.insert(1, path("__msgs__/", site_views.messages_test))
