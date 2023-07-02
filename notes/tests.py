from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from .models import Note

UserModel = get_user_model()


class BasicTests(TestCase):
    def setUp(self):
        self.note = Note.objects.create()
        self.user = UserModel.objects.create_user("juan", "juan@example.com", "1234")

    def test_basic_get_note_views(self):
        response = self.client.get(reverse("notes:create-note"))
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse("notes:my-collection"))
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse("notes:my-collection-by-me"))
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse("notes:not-in-collection-by-me"))
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse("notes:my-collection-by-others"))
        self.assertEqual(response.status_code, 302)
        response = self.client.get(
            reverse("notes:notes-by-username", kwargs={"username": self.user.username})
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse("notes:single-note", kwargs={"slug": self.note.code})
        )
        self.assertEqual(response.status_code, 200)

    def test_basic_get_note_views_authenticated(self):
        self.client.login(username="juan", password="1234")

        response = self.client.get(reverse("notes:create-note"))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("notes:my-collection"))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("notes:my-collection-by-me"))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("notes:not-in-collection-by-me"))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("notes:my-collection-by-others"))
        self.assertEqual(response.status_code, 200)
