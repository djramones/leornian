from django.views.generic import ListView, DetailView
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.core.exceptions import ImproperlyConfigured

from formtools.preview import FormPreview

from .models import Note
from .forms import NoteForm

UserModel = get_user_model()


class _NoteCreate(FormPreview):
    form_template = "notes/note_form.html"
    preview_template = "notes/note_form_preview.html"

    def done(self, request, cleaned_data):
        note = Note(**cleaned_data, author=request.user)
        with transaction.atomic():
            note.save()
            note.collectors.add(request.user)
        messages.add_message(request, messages.SUCCESS, "Note created. 🥳")
        return HttpResponseRedirect(note.get_absolute_url())


create_note = login_required(_NoteCreate(NoteForm))
"""View function for creating a Note with a preview stage."""


class NotesByAuthor(ListView):
    paginate_by = 10

    def get_queryset(self):
        if "username" in self.kwargs:
            author = get_object_or_404(UserModel, username=self.kwargs["username"])
            return Note.objects.filter(
                author=author, visibility=Note.Visibility.NORMAL
            ).select_related("author")

        raise ImproperlyConfigured("'username' keyword argument not supplied.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["author"] = get_object_or_404(
            UserModel, username=self.kwargs["username"]
        )
        return context


class SingleNote(DetailView):
    model = Note
    slug_field = "code"
