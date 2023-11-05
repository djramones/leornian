from django import forms, template
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse, HttpResponseRedirect
from django.utils import safestring
from django.utils import timezone
from django.utils.text import slugify
from django.views.generic import FormView, TemplateView
from django_registration.backends.activation.views import RegistrationView as DjRegView
from markdown_it import MarkdownIt

from leornian_helpers.mixins import CaptchaFormMixin
from notes.views import Start

from . import forms as site_forms
from .services import export_user_data


def home(request):
    if request.user.is_authenticated:
        return Start.as_view()(request)
    return TemplateView.as_view(template_name="home.html")(request)


class TermsAndPrivacy(TemplateView):
    template_name = "terms-and-privacy.html"

    def get_context_data(self, **kwargs):
        # The Terms of Service is written in Markdown with Django template
        # variables. We run it first through the Django template system:
        content = template.loader.render_to_string(
            "terms-and-privacy.md",
            {
                "service_name": settings.TOS_SERVICE_NAME,
                "service_url": settings.TOS_SERVICE_URL,
                "governing_country": settings.TOS_GOVERNING_COUNTRY,
            },
        )
        # before actually rendering to HTML. The source is trusted so
        # we can use default MarkdownIt configuration (usually unsafe):
        content = safestring.mark_safe(MarkdownIt().render(content))
        kwargs.update({"terms_and_privacy": content})
        return super().get_context_data(**kwargs)


class DownloadAccountData(LoginRequiredMixin, CaptchaFormMixin, FormView):
    template_name = "download-account-data.html"
    form_class = forms.Form

    def form_valid(self, form):
        data = export_user_data(self.request)
        file_user = self.request.user.username[:20]  # in case it's too long
        file_user = slugify(file_user)  # to be filename-safe
        file_date = timezone.now().isoformat()[:10]
        filename = f"leornian-data-{file_user}-{file_date}.zip"
        return FileResponse(data, as_attachment=True, filename=filename)


def messages_test(request):
    """
    Add some dummy messages and then redirect to the root URL. Intended for
    development only.
    """
    test_messages = [
        (messages.INFO, "Lorem ipsum dolor, sit amet consectetum."),
        (messages.WARNING, "Oops! Here's a fake warning."),
        (messages.INFO, "Foo bar."),
    ]
    for tag, msg in test_messages:
        messages.add_message(request, tag, msg)
    if "next" in request.GET:
        return HttpResponseRedirect(request.GET["next"])
    return HttpResponseRedirect("/")


class RegistrationView(CaptchaFormMixin, DjRegView):
    form_class = site_forms.RegistrationForm
