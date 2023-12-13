from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import mixins, routers, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Note

UserModel = get_user_model()


class NoteSerializer(serializers.HyperlinkedModelSerializer):
    visibility_label = serializers.StringRelatedField(
        source="get_visibility_display", read_only=True
    )
    author = serializers.StringRelatedField(source="author.username")
    author_url = serializers.HyperlinkedRelatedField(
        source="author",
        view_name="api-notes-by-author-list",
        lookup_field="username",
        read_only=True,
    )

    class Meta:
        model = Note
        fields = [
            "code",
            "url",
            "text",
            "html",
            "visibility",
            "visibility_label",
            "visibility_locked",
            "author",
            "author_url",
            "created",
        ]
        extra_kwargs = {
            "url": {"view_name": "api-notes-detail", "lookup_field": "code"}
        }


class NotePreviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = ["text"]


class NotesByAuthorView(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = NoteSerializer

    def get_queryset(self):
        author = get_object_or_404(UserModel, username=self.kwargs["username"])
        return Note.objects.filter(
            author=author, visibility=Note.Visibility.NORMAL
        ).select_related("author")


class CollectionView(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = NoteSerializer

    def get_queryset(self):
        return self.request.user.collected_notes.select_related("author")


class NotesViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = NoteSerializer
    queryset = Note.objects.all()
    lookup_field = "code"

    @action(
        detail=False,
        methods=["post"],
        serializer_class=NotePreviewSerializer,
        name="Preview HTML",
    )
    def preview_html(self, request):
        """Preview HTML rendering of a given Markdown text."""
        serializer = NotePreviewSerializer(data=request.data)
        if serializer.is_valid():
            html = Note(**serializer.validated_data).html
            return Response({"html": html})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


router = routers.SimpleRouter()
router.register(
    r"@(?P<username>[^/]+)",  # match any non-empty string except `/`
    NotesByAuthorView,
    basename="api-notes-by-author",
)
router.register("collection", CollectionView, basename="api-collection")
router.register("notes", NotesViewSet, basename="api-notes")
