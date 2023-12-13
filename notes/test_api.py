from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Note

UserModel = get_user_model()


class BaseCase(APITestCase):
    def setUp(self):
        self.user = UserModel.objects.create_user("a", "a@example.com", "123")
        self.note = self.user.collected_notes.create(author=self.user)


class NotesByAuthorViewTests(BaseCase):
    def test_get_notes_by_author_list(self):
        """Basic GET requests."""
        response = self.client.get(
            reverse("api-notes-by-author-list", kwargs={"username": "a"})
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            reverse("api-notes-by-author-list", kwargs={"username": "a"})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class CollectionViewTests(BaseCase):
    def test_get_collection_list(self):
        """Basic GET requests."""
        response = self.client.get(reverse("api-collection-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("api-collection-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class NotesViewSetTests(BaseCase):
    def test_get_notes_detail(self):
        """Basic GET requests."""
        response = self.client.get(
            reverse("api-notes-detail", kwargs={"code": self.note.code})
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            reverse("api-notes-detail", kwargs={"code": self.note.code})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_preview_html(self):
        """Basic POST requests."""
        response = self.client.post(
            reverse("api-notes-preview-html"), {"text": "foobar"}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            reverse("api-notes-preview-html"), {"text": "foobar"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_too_long_text(self):
        """Test invalid input (too-long text)."""
        self.client.force_authenticate(user=self.user)
        input_text = "*" * (Note._meta.get_field("text").max_length + 100)
        response = self.client.post(
            reverse("api-notes-preview-html"), {"text": input_text}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
