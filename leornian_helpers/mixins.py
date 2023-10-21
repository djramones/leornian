import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


CAPTCHA_VERIFICATION_ENDPOINT = "https://api.hcaptcha.com/siteverify"
CAPTCHA_FORM_RESPONSE_NAME = "h-captcha-response"


def _verify_form_captcha(request, form, for_anon_only=False):
    if for_anon_only and request.user.is_authenticated:
        return form

    if request.method not in ("POST", "PUT"):
        return form

    if not (token := request.POST.get(CAPTCHA_FORM_RESPONSE_NAME)):
        form.add_error(
            None,
            (
                "Captcha response missing. Please make sure that the captcha"
                " is completed. You may need to enable JavaScript if you have"
                " it disabled."
            ),
        )
        return form

    try:
        result = requests.post(
            CAPTCHA_VERIFICATION_ENDPOINT,
            data={
                "response": token,
                "secret": settings.CAPTCHA_SECRET_KEY,
                "sitekey": settings.CAPTCHA_SITE_KEY,
            },
            timeout=10,
        ).json()
    except requests.RequestException:
        logger.exception("Captcha verification request error.")
        form.add_error(
            None,
            (
                "There was an error in verifying the captcha. The issue could"
                " be temporary and you can try again."
            ),
        )
        return form

    if "success" not in result.keys():
        logger.error("Captcha response has no `success` key.")
        form.add_error(None, "There was an error in verifying the captcha.")
    elif not result["success"]:
        logger.error("Captcha verification error.")
        if "error-codes" not in result.keys():
            logger.error("Captcha error code(s) not found in response.")
        else:
            logger.error("Captcha error code(s): %s", result["error-codes"])
        form.add_error(None, "Captcha verification failed.")

    return form


class CaptchaFormMixin:
    """
    Mixin to add server-side captcha verification to form processing.

    Intended for use with FormMixin-based views.
    """

    captcha_for_anon_only = False

    def get_context_data(self, **kwargs):
        kwargs.update({"captcha_site_key": settings.CAPTCHA_SITE_KEY})
        return super().get_context_data(**kwargs)

    def get_form(self, form_class=None):
        return _verify_form_captcha(
            self.request,
            super().get_form(form_class),
            self.captcha_for_anon_only,
        )
