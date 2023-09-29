from django.urls import path, re_path

from . import views

app_name = "notes"
urlpatterns = [
    path("new/", views.create_note, name="create-note"),
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
    path("@<username>/", views.NotesByAuthor.as_view(), name="notes-by-username"),
    path("discover/", views.Discover.as_view(), name="discover"),
    path("drill/", views.Drill.as_view(), name="drill"),
    re_path(
        r"^(?P<code>[\w-]+)/(?P<action>save|unsave)/$",
        views.CollectionAction.as_view(),
        name="collection-action",
    ),
    path("<slug:slug>/", views.SingleNote.as_view(), name="single-note"),
]
