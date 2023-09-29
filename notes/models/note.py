"""Core note model and related querying logic."""

from django.db import models
from django.db.models import Exists, OuterRef
from django.conf import settings
from django.utils import safestring
from django.urls import reverse

from markdown_it import MarkdownIt

from notes.utils import ChoiceTags, generate_reference_code


class NoteQuerySet(models.QuerySet):
    def annotate_for_controls(self, user):
        if not hasattr(user, "collected_notes"):
            return self
        return self.annotate(
            saved=Exists(user.collected_notes.filter(pk=OuterRef("pk")))
        )

    def get_random(self, for_user=None):
        if for_user:
            qs = self.exclude(collectors=for_user).exclude(author=for_user)
        else:
            qs = self

        qs = qs.exclude(visibility=Note.Visibility.UNLISTED)

        # `order_by("?")` can be slow at scale. See:
        # tech.reversedelay.net/2023/09/optimizing-sql-random-row-select/
        return qs.order_by("?").first()


class Note(models.Model):
    """Core note model."""

    # ------------
    # ENUMERATIONS
    # ------------

    class Visibility(models.IntegerChoices):
        NORMAL = 1
        UNLISTED = 2

    VISIBILITY_TAGS = {
        Visibility.NORMAL: ChoiceTags("success", "eye"),
        Visibility.UNLISTED: ChoiceTags("secondary", "eye-slash"),
    }

    # ------
    # FIELDS
    # ------

    code = models.CharField(
        max_length=9, editable=False, unique=True, default=generate_reference_code
    )
    text = models.TextField(max_length=1200)
    visibility = models.PositiveSmallIntegerField(
        choices=Visibility.choices, default=Visibility.NORMAL
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="authored_notes",
    )
    collectors = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through="Collection", related_name="collected_notes"
    )
    created = models.DateTimeField(auto_now_add=True)

    # --------------------
    # METHODS & PROPERTIES
    # --------------------

    @property
    def html(self):
        """Render safe HTML from the Markdown-formatted `text` field."""
        return safestring.mark_safe(
            MarkdownIt("zero")
            .enable(
                [
                    "emphasis",
                    "strikethrough",
                    "backticks",
                    "entity",
                    "escape",
                    "list",
                ]
            )
            .render(self.text)
        )

    # ----------
    # META, ETC.
    # ----------

    objects = NoteQuerySet.as_manager()

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return str(self.code)

    def get_absolute_url(self):
        return reverse("notes:single-note", kwargs={"slug": self.code})
