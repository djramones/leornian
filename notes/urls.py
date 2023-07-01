from django.urls import path

from .views import create_note, SingleNote

app_name = "notes"
urlpatterns = [
    path("new/", create_note, name="create-note"),
    path("<slug:slug>/", SingleNote.as_view(), name="single-note"),
]
