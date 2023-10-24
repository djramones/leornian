from django.core import mail
from django.core.exceptions import BadRequest
from django.test import RequestFactory, TestCase
from django.urls import reverse

from notes.models import Note

from . import views
from .models import Report, Response
from .utils import generate_date_based_reference_code
from .views import UserModel


class ReportModelTests(TestCase):
    def test_get_absolute_url(self):
        u = UserModel.objects.create()
        r = Report.objects.create(content_object=u)
        # Just make sure it doesn't throw an error:
        self.assertTrue(r.get_absolute_url())


class GenerateDateBasedReferenceCodeTests(TestCase):
    def test_generate(self):
        code = generate_date_based_reference_code()
        self.assertRegex(code[:8], "[0-9]{8}")
        self.assertEqual(code[8], "-")
        self.assertRegex(code[9:], "[0-9A-Z]{8}")
        self.assertEqual(len(code), 17)


class SubmitReportViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.u = UserModel.objects.create_user("u", "u@example.com", "123")
        self.note = Note.objects.create()

    def test_get_as_anon(self):
        res = self.client.get(
            reverse("moderation:submit-report", kwargs={"type": "user", "id": "foo"})
        )
        self.assertEqual(res.status_code, 302)

    def test_get_as_authorized_user(self):
        self.client.login(username="u", password="123")
        res = self.client.get(
            reverse("moderation:submit-report", kwargs={"type": "user", "id": "u"})
        )
        self.assertEqual(res.status_code, 200)

    def test_get_user_content_object(self):
        req = self.factory.get("/test/")
        view = views.SubmitReport()
        view.setup(req, type="user", id="u")
        self.assertEqual(view.get_content_object(), self.u)

    def test_get_note_content_object(self):
        req = self.factory.get("/test/")
        view = views.SubmitReport()
        view.setup(req, type="note", id=self.note.code)
        self.assertEqual(view.get_content_object(), self.note)

    def test_get_content_object_of_unsupported_type(self):
        req = self.factory.get("/test/")
        view = views.SubmitReport()
        view.setup(req, type="foo", id="bar")
        with self.assertRaises(BadRequest):
            view.get_content_object()

    def test_post_as_anon(self):
        res = self.client.post(
            reverse("moderation:submit-report", kwargs={"type": "user", "id": "u"}),
            {"message": "Foobar."},
        )
        self.assertEqual(res.status_code, 302)

    def test_post_as_authorized_user(self):
        self.client.login(username="u", password="123")
        res = self.client.post(
            reverse("moderation:submit-report", kwargs={"type": "user", "id": "u"}),
            {"message": "Foobar."},
            follow=True,
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Report.objects.count(), 1)
        report = Report.objects.all()[0]
        self.assertEqual(report.message, "Foobar.")
        self.assertEqual(report.content_object, self.u)
        self.assertEqual(report.reporter, self.u)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("New content/account report received", mail.outbox[0].subject)


class ReportListViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.u = UserModel.objects.create_user("u", "u@example.com", "123")
        self.staff = UserModel.objects.create_user(
            "s", "s@example.com", "123", is_staff=True
        )
        Report.objects.create(content_object=self.u)
        Report.objects.create(content_object=self.u, reporter=self.u)
        Report.objects.create(content_object=self.u, reporter=self.u)
        Report.objects.create(content_object=self.u, reporter=self.staff)

    def test_get_as_anon(self):
        res = self.client.get(reverse("moderation:report-list"))
        self.assertEqual(res.status_code, 302)

    def test_get_as_authorized_user(self):
        self.client.login(username="u", password="123")
        res = self.client.get(reverse("moderation:report-list"))
        self.assertEqual(res.status_code, 200)

    def test_get_queryset_as_staff(self):
        req = self.factory.get("/test/")
        req.user = self.staff
        view = views.ReportList()
        view.setup(req)
        self.assertEqual(view.get_queryset().count(), 4)

    def test_get_queryset_as_not_staff(self):
        req = self.factory.get("/test/")
        req.user = self.u
        view = views.ReportList()
        view.setup(req)
        self.assertEqual(view.get_queryset().count(), 2)

    def test_get_num_queries(self):
        self.client.login(username="s", password="123")
        with self.assertNumQueries(5):
            res = self.client.get(reverse("moderation:report-list"))
        self.assertEqual(res.status_code, 200)


class ReportAndResponsesDetailsViewTests(TestCase):
    def setUp(self):
        self.u = UserModel.objects.create_user("u", "u@example.com", "123")
        self.staff = UserModel.objects.create_user(
            "s", "s@example.com", "123", is_staff=True
        )
        self.r1 = Report.objects.create(content_object=self.u)
        self.r2 = Report.objects.create(content_object=self.u, reporter=self.u)
        Response.objects.create(report=self.r2, actor=self.u)
        Response.objects.create(report=self.r2, actor=self.staff)

    def test_get_as_anon(self):
        res = self.client.get(
            reverse("moderation:report", kwargs={"code": self.r1.code})
        )
        self.assertEqual(res.status_code, 302)

    def test_get_as_not_staff_and_not_reporter(self):
        self.client.login(username="u", password="123")
        res = self.client.get(
            reverse("moderation:report", kwargs={"code": self.r1.code})
        )
        self.assertEqual(res.status_code, 403)

    def test_get_as_not_staff_and_own_report(self):
        self.client.login(username="u", password="123")
        res = self.client.get(
            reverse("moderation:report", kwargs={"code": self.r2.code})
        )
        self.assertEqual(res.status_code, 200)

    def test_get_as_staff(self):
        self.client.login(username="s", password="123")
        res = self.client.get(
            reverse("moderation:report", kwargs={"code": self.r1.code})
        )
        self.assertEqual(res.status_code, 200)

    def test_get_num_queries(self):
        self.client.login(username="u", password="123")
        res = self.client.get(
            reverse("moderation:report", kwargs={"code": self.r2.code})
        )
        with self.assertNumQueries(8):
            res = self.client.get(
                reverse("moderation:report", kwargs={"code": self.r2.code})
            )
        self.assertEqual(res.status_code, 200)


class AddResponseViewTests(TestCase):
    def setUp(self):
        self.u = UserModel.objects.create_user("u", "u@example.com", "123")
        self.staff = UserModel.objects.create_user(
            "s", "s@example.com", "123", is_staff=True
        )
        self.r1 = Report.objects.create(content_object=self.u)
        self.r2 = Report.objects.create(content_object=self.u, reporter=self.u)

    def test_post_as_anon(self):
        res = self.client.post(
            reverse("moderation:add-response", kwargs={"code": self.r1.code}),
            {"message": "Test response."},
        )
        self.assertEqual(res.status_code, 302)

    def test_post_as_not_staff_and_not_reporter(self):
        self.client.login(username="u", password="123")
        res = self.client.post(
            reverse("moderation:add-response", kwargs={"code": self.r1.code}),
            {"message": "Test response."},
        )
        self.assertEqual(res.status_code, 403)

    def test_post_as_not_staff_and_own_report(self):
        self.client.login(username="u", password="123")
        res = self.client.post(
            reverse("moderation:add-response", kwargs={"code": self.r2.code}),
            {"message": "Test response."},
            follow=True,
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Response.objects.count(), 1)
        response = Response.objects.all()[0]
        self.assertEqual(response.report, self.r2)
        self.assertEqual(response.actor, self.u)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("New response from reporter received", mail.outbox[0].subject)

    def test_post_as_staff(self):
        self.client.login(username="s", password="123")
        res = self.client.post(
            reverse("moderation:add-response", kwargs={"code": self.r2.code}),
            {"message": "Test response."},
            follow=True,
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Response.objects.count(), 1)
        response = Response.objects.all()[0]
        self.assertEqual(response.report, self.r2)
        self.assertEqual(response.actor, self.staff)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(
            "response has been added to your content/account report",
            mail.outbox[0].subject,
        )

    def test_invalid_form(self):
        self.client.login(username="s", password="123")
        too_large_message = "-" * 5100
        res = self.client.post(
            reverse("moderation:add-response", kwargs={"code": self.r1.code}),
            {"message": too_large_message},
        )
        self.assertEqual(res.status_code, 400)
