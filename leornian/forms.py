from django_registration.forms import RegistrationForm as DjRegForm


class RegistrationForm(DjRegForm):
    class Meta(DjRegForm.Meta):
        # The default username-field help-text mentions the 150-char limit,
        # which can be strange for users, so we override to simplify:
        help_texts = {
            "username": (
                "Can contain letters, digits, hyphens, underscores,"
                " periods, and the plus sign."
            )
        }
