from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import mail_admins, send_mail
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView

from .models import Message


def get_message_url(request, message):
    """Get the complete URL for a message, including the scheme and domain."""
    url = "https" if request.is_secure() else "http"
    url += "://" + str(get_current_site(request))
    url += message.get_absolute_url()
    return url


class ContactSupport(CreateView):
    model = Message
    fields = ["subject", "message"]
    template_name = "support/contact_support.html"
    success_url = reverse_lazy("support:contact-done")

    # TODO: add captcha protection if not authenticated

    def form_valid(self, form):
        if self.request.user.is_authenticated:
            form.instance.from_user = self.request.user
        response = super().form_valid(form)
        mail_admins(
            "New message from support contact form",
            "A message has been submitted through the support contact form:\n\n"
            + get_message_url(self.request, self.object),
        )
        return response


class SendSupportMessage(UserPassesTestMixin, SuccessMessageMixin, CreateView):
    model = Message
    fields = ["to_email", "subject", "message"]
    template_name = "support/send_support_message.html"
    success_url = reverse_lazy("support:message-list")
    success_message = "Support message sent."

    def test_func(self):
        return self.request.user.is_staff

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["to_email"].required = True
        return form

    def form_valid(self, form):
        form.instance.from_user = self.request.user
        response = super().form_valid(form)
        send_mail(
            self.object.subject,
            self.object.message,
            from_email=None,  # use DEFAULT_FROM_EMAIL
            recipient_list=[self.object.to_email],
        )
        return response


class MessageList(UserPassesTestMixin, ListView):
    paginate_by = 50

    def test_func(self):
        return self.request.user.is_staff

    def get_queryset(self):
        return Message.objects.all().select_related("from_user")


class MessageDetail(UserPassesTestMixin, DetailView):
    model = Message

    def test_func(self):
        return self.request.user.is_staff
