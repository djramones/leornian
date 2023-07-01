from django.urls import path

from .views import create_note, NotesByAuthor, SingleNote

app_name = "notes"
urlpatterns = [
    path("new/", create_note, name="create-note"),
    path("@<username>/", NotesByAuthor.as_view(), name="notes-by-username"),
    path("<slug:slug>/", SingleNote.as_view(), name="single-note"),
]
