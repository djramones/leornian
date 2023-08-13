from django.views import View
from django.views.generic import ListView, DetailView
from django.core.paginator import Paginator, EmptyPage
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.utils.safestring import mark_safe
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.core.exceptions import ImproperlyConfigured

from formtools.preview import FormPreview

from .models import Note
from .forms import NoteForm

UserModel = get_user_model()


class GracefulPaginator(Paginator):
    """
    django.core.paginator.Paginator modified so that page() behaves
    like get_page() when receiving a page number greater than num_pages.
    Solution from https://stackoverflow.com/a/40835335/14354604.
    """

    def validate_number(self, number):
        try:
            return super().validate_number(number)
        except EmptyPage:
            if number > 1:
                return self.num_pages
            raise


class GracefulListView(ListView):
    paginator_class = GracefulPaginator


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


class NotesByAuthor(GracefulListView):
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


class MyCollection(LoginRequiredMixin, GracefulListView):
    paginate_by = 10
    template_name = "notes/my-collection.html"

    def get_queryset(self):
        return self.request.user.collected_notes.select_related("author")


class MyCollectionByMe(MyCollection):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(author=self.request.user)


class NotInCollectionByMe(MyCollection):
    def get_queryset(self):
        return (
            Note.objects.filter(author=self.request.user)
            .exclude(collectors=self.request.user)
            .select_related("author")
        )


class MyCollectionByOthers(MyCollection):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.exclude(author=self.request.user)


class SingleNote(DetailView):
    model = Note
    slug_field = "code"


class CollectionAction(LoginRequiredMixin, View):
    """View class for saving/unsaving notes and similar actions."""

    def post(self, request, *args, **kwargs):
        action = self.kwargs["action"]
        if action not in ("save", "unsave"):
            raise ImproperlyConfigured("Invalid 'action' keyword argument.")

        note = get_object_or_404(Note, code=self.kwargs["code"])
        if action == "save":
            request.user.collected_notes.add(note)
        elif action == "unsave":
            request.user.collected_notes.remove(note)

        redirect_url = self.request.POST.get("redirect_url", "")

        if action == "save":
            success_msg = "Note saved to collection."
        elif action == "unsave":
            success_msg = "Note removed from collection."
        if redirect_url != note.get_absolute_url():
            # Add link to actioned note to help users with undoing actions,
            # unless the user performed the action from the note detail
            # page itself.
            success_msg += f" <a href='{note.get_absolute_url()}'>"
            if action == "save":
                success_msg += "View saved note</a>"
            elif action == "unsave":
                success_msg += "View removed note</a>"
        success_msg = mark_safe(success_msg)
        messages.add_message(request, messages.SUCCESS, success_msg)

        if url_has_allowed_host_and_scheme(redirect_url, allowed_hosts=None):
            return HttpResponseRedirect(redirect_url)
        return HttpResponseRedirect(note.get_absolute_url())
