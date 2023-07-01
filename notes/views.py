from django.views.generic import DetailView
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction

from formtools.preview import FormPreview

from .models import Note
from .forms import NoteForm


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


class SingleNote(DetailView):
    model = Note
    slug_field = "code"
