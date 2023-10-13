from django.views.generic import TemplateView
from django.contrib import messages
from django.http import HttpResponseRedirect
from django_registration.backends.activation.views import RegistrationView as DjRegView

from notes.views import Start

from . import forms as site_forms


def home(request):
    if request.user.is_authenticated:
        return Start.as_view()(request)
    return TemplateView.as_view(template_name="home.html")(request)


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


class RegistrationView(DjRegView):
    form_class = site_forms.RegistrationForm
