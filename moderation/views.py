from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import BadRequest, PermissionDenied
from django.core.mail import mail_admins, send_mail
from django.forms import modelform_factory
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView

from leornian_helpers.utils import get_object_url
from notes.models import Note

from .models import Report, Response

UserModel = get_user_model()


ResponseForm = modelform_factory(Response, fields=["message"])


class SubmitReport(LoginRequiredMixin, CreateView):
    model = Report
    fields = ["message"]
    success_url = reverse_lazy("moderation:report-list")

    def get_content_object(self):
        if self.kwargs["type"] == "note":
            content_object = get_object_or_404(Note, code=self.kwargs["id"])
        elif self.kwargs["type"] == "user":
            content_object = get_object_or_404(
                UserModel,
                username=self.kwargs["id"],
            )
        else:
            raise BadRequest("Unsupported content type.")
        return content_object

    def get_context_data(self, **kwargs):
        kwargs.update({"content_object": self.get_content_object()})
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        form.instance.content_object = self.get_content_object()
        form.instance.reporter = self.request.user
        response = super().form_valid(form)
        mail_admins(
            "New content/account report received",
            "A report requiring moderator attention has been submitted:\n\n"
            + get_object_url(self.request, self.object),
        )
        messages.success(
            self.request,
            (
                "Thank you, your report has been recorded with"
                f" reference code {self.object.code}."
            ),
        )
        return response


class ReportList(LoginRequiredMixin, ListView):
    paginate_by = 50

    def get_queryset(self):
        if self.request.user.is_staff:
            queryset = Report.objects.all()
        else:
            queryset = Report.objects.filter(reporter=self.request.user)
        return queryset.select_related("content_type").prefetch_related(
            "content_object"
        )


class ReportAndResponsesDetails(LoginRequiredMixin, ListView):
    paginate_by = 10
    template_name = "moderation/report.html"

    def get(self, request, *args, **kwargs):
        self.report = get_object_or_404(Report, code=self.kwargs["code"])
        if not request.user.is_staff and request.user != self.report.reporter:
            raise PermissionDenied
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        kwargs.update({"response_form": ResponseForm()})
        return super().get_context_data(**kwargs)

    def get_queryset(self):
        return Response.objects.filter(report=self.report).select_related("actor")


class AddResponse(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        report = get_object_or_404(Report, code=self.kwargs["code"])
        if not request.user.is_staff and request.user != report.reporter:
            raise PermissionDenied

        form = ResponseForm(request.POST)
        form.instance.report = report
        form.instance.actor = request.user
        if form.is_valid():
            form.save()
        else:
            raise BadRequest("Invalid form.")

        if request.user == report.reporter:
            mail_admins(
                f"New response from reporter received for {report.code}",
                "A reporter has added a response to their report:\n\n"
                + get_object_url(request, report),
            )
        elif report.reporter and report.reporter.email:
            send_mail(
                "A response has been added to your content/account report"
                + f" ({report.code})",
                f"Your report {report.code} has received a new response:\n\n"
                + get_object_url(request, report),
                from_email=None,  # use DEFAULT_FROM_EMAIL
                recipient_list=[report.reporter.email],
            )

        messages.success(request, "Response recorded.")
        return HttpResponseRedirect(
            reverse_lazy("moderation:report", kwargs={"code": report.code})
        )
