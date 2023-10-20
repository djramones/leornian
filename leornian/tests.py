from django.contrib.auth import get_user, get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core import mail
from django.core.handlers.asgi import ASGIHandler
from django.core.handlers.wsgi import WSGIHandler
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase
from django.urls import reverse, resolve

from . import context_processors as ctx_procs
from . import forms as site_forms

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

        # help
        response = self.client.get("/help/")
        self.assertEqual(response.status_code, 200)

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
        self.assertTrue(get_user(self.client).is_authenticated)

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
        self.assertFalse(get_user(self.client).is_authenticated)


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


class DjangoRegistrationTests(TestCase):
    def test_template_smoke_tests(self):
        res = self.client.get(reverse("leornian-register"))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, "django_registration/registration_form.html")

        res = self.client.get(reverse("django_registration_complete"))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, "django_registration/registration_complete.html")

        res = self.client.get(reverse("django_registration_disallowed"))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, "django_registration/registration_closed.html")

        res = self.client.get(
            reverse("django_registration_activate", kwargs={"activation_key": "foobar"})
        )
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, "django_registration/activation_failed.html")

        res = self.client.get(reverse("django_registration_activation_complete"))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, "django_registration/activation_complete.html")

    def test_register_url_override(self):
        """
        Test that even if the overridden URL name is used, reverse() resolves
        to our custom view.
        """
        resolver_match = resolve(reverse("django_registration_register"))
        self.assertEqual(resolver_match.view_name, "leornian-register")

    def test_reg_form_custom_help_text_display(self):
        """Test display of the custom help text."""
        res = self.client.get(reverse("leornian-register"))
        self.assertContains(res, "Can contain letters, digits, hyphens")

    def test_reg_form_other_help_text_display(self):
        """Test display of the other (uncustomized) help texts."""
        res = self.client.get(reverse("leornian-register"))
        self.assertContains(res, "Enter the same password as before")

    def test_reg_form_help_text_validity(self):
        """Test if the custom help text is accurate."""
        form = site_forms.RegistrationForm(
            {
                "username": "a0-_.+",
                "email": "foo@example.com",
                "password1": "whz64rh7wu23wwec",
                "password2": "whz64rh7wu23wwec",
            }
        )
        self.assertTrue(form.is_valid())

    def test_rendered_activation_email_template(self):
        self.client.post(
            reverse("leornian-register"),
            {
                "username": "foo_user",
                "email": "foo@example.com",
                "password1": "whz64rh7wu23wwec",
                "password2": "whz64rh7wu23wwec",
            },
        )
        msg = mail.outbox[0].body
        self.assertIn("Leornian (testserver)", msg)
        self.assertIn("http://testserver/accounts/activate/", msg)


class ContextProcessorsTests(TestCase):
    def test_colormode(self):
        req = RequestFactory().get("/test/")
        self.assertEqual(ctx_procs.colormode(req)["colormode"], None)
        req.COOKIES.update({"colormode": "dark"})
        self.assertEqual(ctx_procs.colormode(req)["colormode"], "dark")
