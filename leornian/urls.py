"""URL configuration for leornian project."""

from django.conf import settings
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import include, path
from django.views.generic import TemplateView
from rest_framework import routers

from notes.api import router as notes_router

from . import views as site_views


admin.site.site_header = admin.site.site_title = "Leornian admin"

# API router
router = routers.DefaultRouter()
router.APIRootView.name = "API Root"
router.APIRootView.description = "The Leornian API root resource."
router.registry.extend(notes_router.registry)


urlpatterns = [
    path("api/accounts/", include("rest_framework.urls")),
    path("api/", include(router.urls)),
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
    path(
        "accounts/download-account-data/",
        site_views.DownloadAccountData.as_view(),
        name="download-account-data",
    ),
    path("about/", TemplateView.as_view(template_name="about.html"), name="about"),
    path("help/", TemplateView.as_view(template_name="help.html"), name="help"),
    path(
        "terms-and-privacy/",
        site_views.TermsAndPrivacy.as_view(),
        name="terms-and-privacy",
    ),
    path(
        "content-license/",
        TemplateView.as_view(template_name="content-license.html"),
        name="content-license",
    ),
    path("support/", include("support.urls")),
    path("moderation/", include("moderation.urls")),
    path("", include("notes.urls")),
    path("", site_views.home, name="home"),
]

if settings.DEBUG:
    urlpatterns.insert(0, path("__debug__/", include("debug_toolbar.urls")))
    urlpatterns.insert(1, path("__msgs__/", site_views.messages_test))
