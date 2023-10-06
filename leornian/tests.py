from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.handlers.asgi import ASGIHandler
from django.core.handlers.wsgi import WSGIHandler
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase
from django.urls import reverse, resolve

from . import views

UserModel = get_user_model()


class BasicTests(TestCase):
    def test_basic_requests_unauthenticated(self):
        UserModel.objects.create_user("mary", "mary@example.com", "1234")

        # home
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        # my-account
        response = self.client.get("/accounts/me/")
        self.assertRedirects(response, "/accounts/login/?next=/accounts/me/")

        # Admin views
        response = self.client.get("/admin/")
        self.assertRedirects(response, "/admin/login/?next=/admin/")

        # Auth views
        response = self.client.get("/accounts/login/")
        self.assertEqual(response.status_code, 200)

        # Auth: perform login
        response = self.client.post(
            "/accounts/login/", {"username": "mary", "password": "1234"}
        )
        self.assertRedirects(response, "/")

    def test_basic_requests_authenticated(self):
        UserModel.objects.create_user("mary", "mary@example.com", "1234")
        self.client.login(username="mary", password="1234")

        # home
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        # my-account
        response = self.client.get("/accounts/me/")
        self.assertEqual(response.status_code, 200)

        # Auth: perform logout
        response = self.client.post("/accounts/logout/")
        self.assertRedirects(response, "/")


class XSGISmokeTests(TestCase):
    def test_asgi_import(self):
        from leornian import asgi

        self.assertIs(type(asgi.application), ASGIHandler)

    def test_wsgi_import(self):
        from leornian import wsgi

        self.assertIs(type(wsgi.application), WSGIHandler)


class ViewsTests(TestCase):
    def test_home_view(self):
        UserModel.objects.create_user("mary", "mary@example.com", "1234")

        # Unauthenticated
        res = self.client.get(reverse("home"))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, "home.html")

        # Authenticated
        self.client.login(username="mary", password="1234")
        res = self.client.get(reverse("home"))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, "notes/start.html")


class TemplatesTests(TestCase):
    def test_base_html(self):
        req = RequestFactory().get("/test/")
        anon = AnonymousUser()
        user = UserModel.objects.create_user("mary", "mary@example.com", "1234")

        # Unauthenticated: home
        req.resolver_match = resolve(reverse("home"))
        out = render_to_string("base.html", {"request": req, "user": anon})
        self.assertNotIn("Start", out)

        # Authenticated: home
        req.resolver_match = resolve(reverse("home"))
        out = render_to_string("base.html", {"request": req, "user": user})
        self.assertInHTML(
            f'<a class="nav-link active" href="{reverse("home")}">Start</a>', out
        )

        # Authenticated: notes:create-note
        req.resolver_match = resolve(reverse("notes:create-note"))
        out = render_to_string("base.html", {"request": req, "user": user})
        self.assertInHTML(
            f'<a class="nav-link icon-link active" href="{reverse("notes:create-note")}"><i class="bi-file-earmark-plus"></i><span class="d-none d-lg-block">New Note</span></a>',
            out,
        )

        # Authenticated: notes:my-collection
        req.resolver_match = resolve(reverse("notes:my-collection"))
        out = render_to_string("base.html", {"request": req, "user": user})
        self.assertInHTML(
            f'<a class="nav-link icon-link active" href="{reverse("notes:my-collection")}"><i class="bi-collection"></i><span class="d-none d-lg-block">Collection</span></a>',
            out,
        )

        # Unauthenticated: login
        req.resolver_match = resolve(reverse("login"))
        out = render_to_string("base.html", {"request": req, "user": anon})
        self.assertInHTML(
            f'<a class="nav-link icon-link active" href="{reverse("login")}"><i class="bi-box-arrow-in-right"></i> Log In</a>',
            out,
        )

        # Authenticated: my-account
        req.resolver_match = resolve(reverse("my-account"))
        out = render_to_string("base.html", {"request": req, "user": user})
        self.assertInHTML(
            f'<a class="nav-link icon-link active" href="{reverse("my-account")}"><i class="bi-person-circle"></i><span class="d-none d-lg-block">Account</span></a>',
            out,
        )

    def test_base_html_through_view(self):
        """
        Test the base template, which uses request.resolver_match, through a
        view call.
        """
        UserModel.objects.create_user("mary", "mary@example.com", "1234")
        self.client.login(username="mary", password="1234")
        res = self.client.get(reverse("home"))
        self.assertContains(
            res,
            f'<a class="nav-link active" href="{reverse("home")}">Start</a>',
            html=True,
        )


class URLsTests(TestCase):
    def test_urls(self):
        self.assertEqual(resolve("/").view_name, "home")

        # Notes URLs integration
        self.assertEqual(resolve("/new/").view_name, "notes:create-note")
        self.assertEqual(resolve("/foobar/").view_name, "notes:single-note")

        # django.contrib.auth integration
        self.assertEqual(resolve("/accounts/login/").view_name, "login")

        # django.contrib.admin integration
        self.assertEqual(resolve("/admin/login/").view_name, "admin:login")
