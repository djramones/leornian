from django.test import TestCase
from django.urls import reverse

from .models import Note


class BasicTests(TestCase):
    def test_get_single_note(self):
        n = Note.objects.create()
        response = self.client.get(
            reverse("notes:single-note", kwargs={"slug": n.code})
        )
        self.assertEqual(response.status_code, 200)
