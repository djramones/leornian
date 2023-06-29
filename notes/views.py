from django.views.generic import DetailView

from .models import Note


class SingleNote(DetailView):
    model = Note
    slug_field = "code"
