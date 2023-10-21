from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import RequestFactory, TestCase
from django.urls import reverse

from .models import Message
from . import views


UserModel = get_user_model()


class GetMessageURLTests(TestCase):
    def test_get_message_url_function(self):
        req = RequestFactory().get("/test/")
        message = Message.objects.create(subject="Foo", message="Bar")
        url = views.get_message_url(req, message)
        self.assertEqual(url, "http://testserver" + message.get_absolute_url())


class ContactSupportTests(TestCase):
    def setUp(self):
        self.user = UserModel.objects.create_user("mary", "mary@example.com", "1234")

    def test_basic_get(self):
        res = self.client.get(reverse("support:contact"))
        self.assertEqual(res.status_code, 200)

    @patch("leornian_helpers.mixins._verify_form_captcha")
    def test_submit_as_anonymous_user(self, mock_verify_captcha):
        # Mock _verify_form_captcha to simply return the form object passed
        # to it, to skip the external verification request:
        mock_verify_captcha.side_effect = lambda *args: args[1]
        res = self.client.post(
            reverse("support:contact"),
            {
                "subject": "Foo",
                "message": "Bar.",
                "h-captcha-response": "10000000-aaaa-bbbb-cccc-000000000001",
            },
        )
        self.assertEqual(res.status_code, 302)
        self.assertEqual(Message.objects.count(), 1)
        msg = Message.objects.all()[0]
        self.assertEqual(msg.from_user, None)
        self.assertEqual(len(mail.outbox), 1)

    def test_submit_as_authenticated_user(self):
        self.client.login(username="mary", password="1234")
        res = self.client.post(
            reverse("support:contact"), {"subject": "Foo", "message": "Bar."}
        )
        self.assertEqual(res.status_code, 302)
        self.assertEqual(Message.objects.count(), 1)
        msg = Message.objects.all()[0]
        self.assertEqual(msg.from_user, self.user)
        self.assertEqual(len(mail.outbox), 1)

    def test_follow_success_url(self):
        res = self.client.post(
            reverse("support:contact"),
            {"subject": "Foo", "message": "Bar."},
            follow=True,
        )
        self.assertEqual(res.status_code, 200)


class SendSupportMessageTests(TestCase):
    def setUp(self):
        self.user = UserModel.objects.create_user(
            "mary", "mary@example.com", "1234", is_staff=True
        )

    def test_user_is_not_authenticated(self):
        res = self.client.get(reverse("support:send-support-message"))
        self.assertEqual(res.status_code, 302)

    def test_user_is_not_staff(self):
        UserModel.objects.create_user("x", "x@example.com", "1234")
        self.client.login(username="x", password="1234")
        res = self.client.get(reverse("support:send-support-message"))
        self.assertEqual(res.status_code, 403)

    def test_required_to_email(self):
        self.client.login(username="mary", password="1234")
        res = self.client.post(
            reverse("support:send-support-message"),
            {"to_email": "", "subject": "Foo", "message": "Bar."},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Message.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_normal_successful_post(self):
        self.client.login(username="mary", password="1234")
        res = self.client.post(
            reverse("support:send-support-message"),
            {"to_email": "x@example.com", "subject": "Foo", "message": "Bar."},
            follow=True,
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Message.objects.count(), 1)
        msg = Message.objects.all()[0]
        self.assertEqual(msg.from_user, self.user)
        self.assertEqual(len(mail.outbox), 1)


class MessageListTests(TestCase):
    def setUp(self):
        self.user = UserModel.objects.create_user(
            "mary", "mary@example.com", "1234", is_staff=True
        )

    def test_user_is_not_authenticated(self):
        res = self.client.get(reverse("support:message-list"))
        self.assertEqual(res.status_code, 302)

    def test_no_messages(self):
        self.client.login(username="mary", password="1234")
        res = self.client.get(reverse("support:message-list"))
        self.assertEqual(res.status_code, 200)

    def test_with_messages(self):
        self.client.login(username="mary", password="1234")
        for _ in range(3):
            Message.objects.create(subject="Foo", message="Bar")
        res = self.client.get(reverse("support:message-list"))
        self.assertEqual(res.status_code, 200)


class MessageDetailTests(TestCase):
    def setUp(self):
        self.user = UserModel.objects.create_user(
            "mary", "mary@example.com", "1234", is_staff=True
        )
        self.msg = Message.objects.create(subject="Foo", message="Bar")

    def test_user_is_not_authenticated(self):
        res = self.client.get(
            reverse("support:message-detail", kwargs={"pk": self.msg.pk})
        )
        self.assertEqual(res.status_code, 302)

    def test_with_messages(self):
        self.client.login(username="mary", password="1234")
        res = self.client.get(
            reverse("support:message-detail", kwargs={"pk": self.msg.pk})
        )
        self.assertEqual(res.status_code, 200)
