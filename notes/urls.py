from django.urls import path, re_path

from . import views

app_name = "notes"
urlpatterns = [
    path("new/", views.create_note, name="create-note"),
    path(
        "<slug:slug>/visibility/change/",
        views.ChangeNoteVisibility.as_view(),
        name="change-vis",
    ),
    path("<slug:slug>/delete/", views.DeleteNote.as_view(), name="delete-note"),
    path(
        "<slug:slug>/deattribute/",
        views.RemoveAttribution.as_view(),
        name="deattribute",
    ),
    path(
        "<slug:slug>/reattribute/",
        views.RestoreAttribution.as_view(),
        name="reattribute",
    ),
    path("collection/", views.MyCollection.as_view(), name="my-collection"),
    path(
        "collection/by-me/",
        views.MyCollectionByMe.as_view(),
        name="my-collection-by-me",
    ),
    path(
        "not-in-collection/by-me/",
        views.NotInCollectionByMe.as_view(),
        name="not-in-collection-by-me",
    ),
    path(
        "collection/by-others/",
        views.MyCollectionByOthers.as_view(),
        name="my-collection-by-others",
    ),
    path(
        "collection/promoted/",
        views.MyCollectionPromoted.as_view(),
        name="my-collection-promoted",
    ),
    path("deattributed/", views.DeattributedNotes.as_view(), name="deattributed-notes"),
    path("@<username>/", views.NotesByAuthor.as_view(), name="notes-by-username"),
    path("discover/", views.Discover.as_view(), name="discover"),
    path("drill/", views.Drill.as_view(), name="drill"),
    re_path(
        # Same as "<slug:code>/<action>/" where <action> is save or unsave:
        r"^(?P<code>[\w-]+)/(?P<action>save|unsave)/$",
        views.CollectionAction.as_view(),
        name="collection-action",
    ),
    path("<slug:slug>/", views.SingleNote.as_view(), name="single-note"),
]
