from django.contrib.auth import get_user_model
from django.core.handlers.asgi import ASGIHandler
from django.core.handlers.wsgi import WSGIHandler
from django.test import TestCase

UserModel = get_user_model()


class BasicTests(TestCase):
    def test_basic_requests_unauthenticated(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/accounts/me/")
        self.assertRedirects(response, "/accounts/login/?next=/accounts/me/")

        # Admin views
        response = self.client.get("/admin/")
        self.assertRedirects(response, "/admin/login/?next=/admin/")

        # Auth views
        response = self.client.get("/accounts/login/")
        self.assertEqual(response.status_code, 200)
        response = self.client.post("/accounts/logout/")
        self.assertRedirects(response, "/")

    def test_basic_requests_authenticated(self):
        UserModel.objects.create_user("mary", "mary@example.com", "1234")
        self.client.login(username="mary", password="1234")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)


class XSGISmokeTests(TestCase):
    def test_asgi_import(self):
        from leornian import asgi

        self.assertIs(type(asgi.application), ASGIHandler)

    def test_wsgi_import(self):
        from leornian import wsgi

        self.assertIs(type(wsgi.application), WSGIHandler)
