from django import template
from django.urls import reverse

register = template.Library()


@register.inclusion_tag("notes/templatetags/note_controls.html")
def note_controls(note, request):
    main_controls = []
    more_controls = []

    if request.user.is_authenticated:
        if not note.saved:
            # Save note to collection
            main_controls.append(
                {
                    "method": "post",
                    "action": reverse(
                        "notes:collection-action",
                        kwargs={"code": note.code, "action": "save"},
                    ),
                    "icon": "plus-circle",
                    "text": "Save",
                }
            )
        else:
            # Unsave note from collection
            main_controls.append(
                {
                    "method": "post",
                    "action": reverse(
                        "notes:collection-action",
                        kwargs={"code": note.code, "action": "unsave"},
                    ),
                    "icon": "x-circle",
                    "text": "Unsave",
                }
            )
        if note.author == request.user:
            # Delete note
            more_controls.append(
                {
                    "method": "get",
                    "action": reverse(
                        "notes:delete-note",
                        kwargs={"slug": note.code},
                    ),
                    "icon": "trash",
                    "text": "Delete",
                }
            )

    return {
        "main_controls": main_controls,
        "more_controls": more_controls,
        "request": request,
    }
