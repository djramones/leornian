import itertools
import random

from django.views import View
from django.views.generic import ListView, DetailView, TemplateView
from django.core.paginator import Paginator, EmptyPage
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.utils.safestring import mark_safe
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.urls import reverse
from django.utils import timezone

from formtools.preview import FormPreview

from .models import Note, Collection
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
            return (
                Note.objects.filter(author=author, visibility=Note.Visibility.NORMAL)
                .select_related("author")
                .annotate_for_controls(self.request.user)
            )

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
        return self.request.user.collected_notes.select_related(
            "author"
        ).annotate_for_controls(self.request.user)


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
            .annotate_for_controls(self.request.user)
        )


class MyCollectionByOthers(MyCollection):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.exclude(author=self.request.user)


class MyCollectionPromoted(MyCollection):
    def get_queryset(self):
        return (
            Note.objects.filter(collectors=self.request.user, collection__promoted=True)
            .select_related("author")
            .annotate_for_controls(self.request.user)
        )


class SingleNote(DetailView):
    model = Note
    slug_field = "code"

    def get_queryset(self):
        return super().get_queryset().annotate_for_controls(self.request.user)


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


class Discover(View):
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            note = Note.objects.get_random()
        else:
            note = Note.objects.get_random(for_user=request.user)
        return render(request, "notes/discover.html", {"note": note})

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied

        note = get_object_or_404(Note, code=request.POST.get("code"))
        request.user.collected_notes.add(note)

        success_msg = (
            "A note has been saved to your collection."
            + f" <a href='{note.get_absolute_url()}'>View saved note</a>"
        )
        success_msg = mark_safe(success_msg)
        messages.add_message(request, messages.SUCCESS, success_msg)

        return HttpResponseRedirect(reverse("notes:discover"))


class Drill(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        coll_count = Collection.objects.filter(user=request.user).count()
        disable_begin = True if coll_count < 2 else False
        recent_drill_count = Collection.objects.filter(
            user=request.user,
            last_drilled__gt=timezone.now() - timezone.timedelta(hours=24),
        ).count()
        return render(
            request,
            "notes/drill.html",
            {"disable_begin": disable_begin, "recent_drill_count": recent_drill_count},
        )

    def post(self, request, *args, **kwargs):
        if promote_code := request.POST.get("promote"):
            # Make sure to filter by user to prevent modifying other users' data
            Collection.objects.filter(
                note__code=promote_code, user=request.user
            ).update(promoted=True)
            messages.add_message(request, messages.SUCCESS, "A note has been promoted.")
        if demote_code := request.POST.get("demote"):
            Collection.objects.filter(note__code=demote_code, user=request.user).update(
                promoted=False
            )
            messages.add_message(request, messages.SUCCESS, "A note has been demoted.")

        values = (
            Collection.objects.filter(user=request.user)
            .order_by("-last_drilled")
            .values_list("id", "note_id", "promoted")
        )
        unzipped_values = tuple(zip(*values))
        # Collection must have at least two notes:
        if not unzipped_values or len(unzipped_values[0]) < 2:
            return render(
                request, "notes/drill.html", {"error": "insufficient-collection"}
            )
        # Last-drilled note should not be picked, hence `[1:]`:
        coll_pks, note_pks = unzipped_values[0][1:], unzipped_values[1][1:]
        promoted_vals = unzipped_values[2][1:]
        # By default, weights drawn from standard power function distribution:
        n, p = len(coll_pks), 5
        weights = [p * ((x / n) ** (p - 1)) for x in range(1, n + 1)]
        # Promoted items have weights drawn from a linear function:
        for index in itertools.compress(range(n), promoted_vals):
            weights[index] = p * ((index + 1) / n)
        draw_index = random.choices(range(n), weights)[0]
        note = Note.objects.select_related("author").get(pk=note_pks[draw_index])
        promoted = Collection.objects.get(id=coll_pks[draw_index]).promoted

        Collection.objects.filter(id=coll_pks[draw_index]).update(
            last_drilled=timezone.now()
        )

        recent_drill_count = Collection.objects.filter(
            user=request.user,
            last_drilled__gt=timezone.now() - timezone.timedelta(hours=24),
        ).count()
        return render(
            request,
            "notes/drill.html",
            {
                "note": note,
                "promoted": promoted,
                "recent_drill_count": recent_drill_count,
            },
        )


class Start(TemplateView):
    template_name = "notes/start.html"
