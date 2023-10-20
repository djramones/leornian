from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = "support"
urlpatterns = [
    path("contact/", views.ContactSupport.as_view(), name="contact"),
    path(
        "contact/done/",
        TemplateView.as_view(template_name="support/contact_support_done.html"),
        name="contact-done",
    ),
    path(
        "messages/send/",
        views.SendSupportMessage.as_view(),
        name="send-support-message",
    ),
    path("messages/", views.MessageList.as_view(), name="message-list"),
    path("messages/<uuid:pk>/", views.MessageDetail.as_view(), name="message-detail"),
]
