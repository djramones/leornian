"""Custom template tags & filters for `notes`."""

from django import template

register = template.Library()


@register.inclusion_tag("notes/templatetags/note_vis_badge.html")
def note_vis_badge(note):
    """
    Given a Note, render a Bootstrap badge with the appropriate
    background color.
    """
    return {
        "tags": note.VISIBILITY_TAGS[note.visibility],
        "label": note.get_visibility_display(),
    }
