from django.urls import path

from . import views

app_name = "moderation"
urlpatterns = [
    path(
        "report/<type>/<id>/",
        views.SubmitReport.as_view(),
        name="submit-report",
    ),
    path(
        "reports/",
        views.ReportList.as_view(),
        name="report-list",
    ),
    path(
        "reports/<slug:code>/",
        views.ReportAndResponsesDetails.as_view(),
        name="report",
    ),
    path(
        "reports/<slug:code>/respond/",
        views.AddResponse.as_view(),
        name="add-response",
    ),
]
