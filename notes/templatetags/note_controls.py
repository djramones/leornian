from django import template
from django.urls import reverse

register = template.Library()


@register.inclusion_tag("notes/templatetags/note_controls.html")
def note_controls(note, request):
    controls = []

    if request.user.is_authenticated:
        if note not in request.user.collected_notes.all():
            # Save note to collection
            controls.append(
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
            controls.append(
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

    return {"controls": controls, "request": request}
