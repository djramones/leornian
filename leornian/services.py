"""Services for the Leornian project."""

import csv
import io
import json
from datetime import datetime
from zipfile import ZIP_DEFLATED, ZipFile

from leornian_helpers.utils import get_object_url


def export_user_data(request) -> io.BytesIO:
    """Export relevant user account data to a zipped archive."""

    # Note: this initial implementation is not designed
    # to be scalable, and violates app decoupling.

    # Fetch and transform notes data
    queryset = request.user.collection_set.all()
    queryset = queryset.select_related("note", "note__author")
    queryset = queryset.order_by("note__created")
    notes_data = []
    for item in queryset:
        # We cannot use values_list because we need to do some transforms.
        notes_data.append(
            {
                "Note Code": item.note.code,
                "Text": item.note.text,
                "HTML": item.note.html,
                "Visibility": item.note.get_visibility_display(),
                "Created": item.note.created.isoformat(),
                "Author": item.note.author.username if item.note.author else "",
                "Permalink": get_object_url(request, item.note),
                "Last Drilled": item.last_drilled.isoformat(),
                "Promoted?": item.promoted,
            }
        )

    # Format notes data as CSV, and encode as UTF-8 with BOM for better Excel
    # compatibility
    notes_data_csv = io.StringIO()
    if len(notes_data) > 0:
        fieldnames = list(notes_data[0].keys())
        csvwriter = csv.DictWriter(notes_data_csv, fieldnames=fieldnames)
        csvwriter.writeheader()
        csvwriter.writerows(notes_data)
    notes_data_csv = notes_data_csv.getvalue().encode("utf-8-sig")

    # Format notes data as JSON
    notes_data_json = json.dumps(notes_data, indent=4)

    # Prepare README.txt
    readme = (
        "This is the archive of data for Leornian user account"
        f" `{request.user.username}`.\n\n"
        f"User account email: {request.user.email}\n"
        f"Account created at: {request.user.date_joined}\n\n"
        f"Number of notes in collection: {len(notes_data)}\n\n"
        "The CSV file in this archive is encoded in UTF-8 with BOM for"
        " compatibility with Microsoft applications (especially Excel).\n\n"
        f"This archive was generated at {datetime.now().isoformat()} (UTC).\n"
    )

    # Save into compressed archive in memory
    buffer = io.BytesIO()
    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as zipf:
        zipf.writestr("collected_notes.csv", notes_data_csv)
        zipf.writestr("collected_notes.json", notes_data_json)
        zipf.writestr("README.txt", readme)
    buffer.seek(0)

    return buffer
