import logging
from unittest.mock import patch

import requests
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase
from django.views.generic import FormView

from .mixins import CAPTCHA_FORM_RESPONSE_NAME, CaptchaFormMixin, _verify_form_captcha

UserModel = get_user_model()


class DummyForm(forms.Form):
    pass


class TestCaptchaFormMixinView(CaptchaFormMixin, FormView):
    form_class = DummyForm


class VerifyFormCaptchaTests(TestCase):
    def setUp(self):
        factory = RequestFactory()
        post_payload = {
            CAPTCHA_FORM_RESPONSE_NAME: "10000000-aaaa-bbbb-cccc-000000000001"
        }
        user = UserModel.objects.create_user("u", "u@example.com", "123")

        self.post_req_auth = factory.post("/test/")
        self.post_req_auth.user = user

        self.get_req = factory.get("/test/")
        self.get_req.user = AnonymousUser()

        self.post_req_blank = factory.post("/test/")
        self.post_req_blank.user = AnonymousUser()

        self.post_req = factory.post("/test/", post_payload)
        self.post_req.user = AnonymousUser()

        logging.disable(logging.CRITICAL)

    def tearDown(self):
        logging.disable(logging.NOTSET)

    def test_skip_for_authenticated_user(self):
        form = _verify_form_captcha(
            self.post_req_auth, DummyForm({}), for_anon_only=True
        )
        self.assertTrue(form.is_valid())

    def test_skip_if_not_post_or_put(self):
        form = _verify_form_captcha(self.get_req, DummyForm({}))
        self.assertTrue(form.is_valid())

    def test_no_captcha_response_in_post_data(self):
        form = _verify_form_captcha(self.post_req_blank, DummyForm({}))
        self.assertFalse(form.is_valid())
        self.assertIn("response missing", str(form.errors))

    @patch("requests.post")
    def test_http_error(self, mock_post):
        mock_post.side_effect = requests.exceptions.HTTPError
        form = _verify_form_captcha(self.post_req, DummyForm({}))
        self.assertFalse(form.is_valid())
        self.assertIn("error in verifying the captcha", str(form.errors))

    @patch("requests.Response.json")
    @patch("requests.post")
    def test_response_has_no_success_key(self, mock_post, mock_json):
        mock_post.return_value = requests.Response()
        mock_json.return_value = {}
        form = _verify_form_captcha(self.post_req, DummyForm({}))
        self.assertFalse(form.is_valid())
        self.assertIn("error in verifying the captcha", str(form.errors))

    @patch("requests.Response.json")
    @patch("requests.post")
    def test_failed_with_no_error_code(self, mock_post, mock_json):
        mock_post.return_value = requests.Response()
        mock_json.return_value = {"success": False}
        form = _verify_form_captcha(self.post_req, DummyForm({}))
        self.assertFalse(form.is_valid())
        self.assertIn("Captcha verification failed", str(form.errors))

    @patch("requests.Response.json")
    @patch("requests.post")
    def test_failed_with_error_code(self, mock_post, mock_json):
        mock_post.return_value = requests.Response()
        mock_json.return_value = {
            "success": False,
            "error-codes": ["bad-request"],
        }
        form = _verify_form_captcha(self.post_req, DummyForm({}))
        self.assertFalse(form.is_valid())
        self.assertIn("Captcha verification failed", str(form.errors))

    @patch("requests.Response.json")
    @patch("requests.post")
    def test_good_captcha(self, mock_post, mock_json):
        mock_post.return_value = requests.Response()
        mock_json.return_value = {"success": True}
        form = _verify_form_captcha(self.post_req, DummyForm({}))
        self.assertTrue(form.is_valid())


class CaptchaFormMixinTests(TestCase):
    def setUp(self):
        req = RequestFactory().get("/test/")
        self.view = TestCaptchaFormMixinView()
        self.view.setup(req)

    def test_captcha_site_key_in_context(self):
        self.assertIn("captcha_site_key", self.view.get_context_data().keys())

    def test_get_form_return(self):
        self.assertIsInstance(self.view.get_form(), DummyForm)
