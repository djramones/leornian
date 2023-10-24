from django.contrib import admin

from .models import Note


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    # These settings are intended only to accommodate moderation operations.
    fields = ["visibility", "visibility_locked"]
    list_display = [
        "code",
        "visibility",
        "visibility_locked",
        "author",
        "created",
    ]
    list_select_related = ["author"]  # needed to fix N+1 queries
    list_filter = ["visibility", "visibility_locked"]
    date_hierarchy = "created"
    search_fields = ["code", "author__username"]
