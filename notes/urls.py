from django.urls import path

from .views import SingleNote

app_name = "notes"
urlpatterns = [
    path("<slug:slug>/", SingleNote.as_view(), name="single-note"),
]
