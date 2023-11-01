from django import forms
from django.urls import reverse_lazy
from django.utils import safestring
from django.utils.text import format_lazy
from django_registration.forms import RegistrationForm as DjRegForm


class RegistrationForm(DjRegForm):
    terms_acceptance = forms.BooleanField(
        label=safestring.mark_safe(
            format_lazy(
                (
                    "I have read and agree to the <a href='{terms_link}'>"
                    "Terms of Service and Privacy Policy</a>"
                ),
                terms_link=reverse_lazy("terms-and-privacy"),
            )
        ),
        error_messages={
            "required": (
                "You must agree to the Terms of Service and Privacy"
                " Policy to create an account."
            )
        },
    )

    class Meta(DjRegForm.Meta):
        # The default username-field help-text mentions the 150-char limit,
        # which can be strange for users, so we override to simplify. This
        # also drops mention of the `@` character, which we don't want to
        # encourage.
        help_texts = {
            "username": (
                "Can contain letters, digits, hyphens, underscores,"
                " periods, and the plus sign."
            )
        }
