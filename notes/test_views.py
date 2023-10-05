import formtools
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.views.generic import ListView

from . import views
from .models import Collection, Note

UserModel = get_user_model()


class ViewsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = UserModel.objects.create_user("juan", "juan@example.com", "1234")

    def test_GracefulListView(self):
        Note.objects.create(text="Foo")
        req = self.factory.get("/test/", {"page": 2})
        req.user = AnonymousUser()

        # Test default ListView behavior:
        with self.assertRaises(Http404):
            ListView.as_view(model=Note, paginate_by=10)(req)
        # GracefulListView, meanwhile, should not 404:
        res = views.GracefulListView.as_view(model=Note, paginate_by=10)(req)
        self.assertEqual(res.status_code, 200)
        # Negative page numbers should still 404:
        req = RequestFactory().get("/test/", {"page": -1})
        req.user = AnonymousUser()
        with self.assertRaises(Http404):
            res = views.GracefulListView.as_view(model=Note, paginate_by=10)(req)

    def test_create_note_view(self):
        self.client.login(username="juan", password="1234")

        # GET initial form
        res = self.client.get(reverse("notes:create-note"))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, "notes/note_form.html")

        # POST to preview
        res = self.client.post(
            reverse("notes:create-note"),
            {"text": "Foo *bar*.", "visibility": Note.Visibility.NORMAL, "stage": 1},
        )
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, "notes/note_form_preview.html")

        # POST to submit
        form_hash = formtools.utils.form_hmac(
            views.NoteForm({"text": "Foo *bar*.", "visibility": Note.Visibility.NORMAL})
        )
        res = self.client.post(
            reverse("notes:create-note"),
            {
                "text": "Foo *bar*.",
                "visibility": Note.Visibility.NORMAL,
                "stage": 2,
                "hash": form_hash,
            },
        )
        self.assertEqual(res.status_code, 302)
        self.assertEqual(Note.objects.count(), 1)
        note = Note.objects.all()[0]
        self.assertEqual(note.text, "Foo *bar*.")
        self.assertEqual(Collection.objects.count(), 1)
        self.assertEqual(self.user.collected_notes.all()[0].id, note.id)

    def test_NotesByAuthor_view(self):
        req = self.factory.get("/test/")
        req.user = AnonymousUser()

        with self.assertRaises(ImproperlyConfigured):
            views.NotesByAuthor.as_view()(req)

        with self.assertRaises(Http404):
            views.NotesByAuthor.as_view()(req, username="nonexistentuser")

        # Check get_queryset():
        view = views.NotesByAuthor()
        view.setup(req, username=self.user.username)
        self.assertEqual(len(view.get_queryset()), 0)
        note = Note.objects.create()
        self.assertNotIn(note, view.get_queryset())
        note = Note.objects.create(
            author=self.user, visibility=Note.Visibility.UNLISTED
        )
        self.assertNotIn(note, view.get_queryset())
        note = Note.objects.create(author=self.user)
        self.assertIn(note, view.get_queryset())

        for _ in range(3):
            # Create multiple objects for testing for N+1 queries:
            Note.objects.create(author=self.user)
        with self.assertNumQueries(4):  # test for N+1 queries
            res = self.client.get(
                reverse(
                    "notes:notes-by-username", kwargs={"username": self.user.username}
                )
            )
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, "notes/note_list.html")

    def test_MyCollection_view(self):
        req = self.factory.get("/test/")
        req.user = self.user
        view = views.MyCollection()
        view.setup(req)

        Note.objects.create()
        self.user.collected_notes.create(author=self.user)
        self.assertEqual(len(view.get_queryset()), 1)

        # Test for N+1 queries:
        for _ in range(3):
            self.user.collected_notes.create(author=self.user)
        self.client.login(username="juan", password="1234")
        with self.assertNumQueries(4):
            self.client.get(reverse("notes:my-collection"))

    def test_MyCollectionByMe_view(self):
        req = self.factory.get("/test/")
        req.user = self.user
        view = views.MyCollectionByMe()
        view.setup(req)

        self.user.collected_notes.create()
        self.user.collected_notes.create(author=self.user)
        self.assertEqual(len(view.get_queryset()), 1)

        # Test for N+1 queries:
        for _ in range(3):
            self.user.collected_notes.create(author=self.user)
        self.client.login(username="juan", password="1234")
        with self.assertNumQueries(4):
            self.client.get(reverse("notes:my-collection-by-me"))

    def test_NotInCollectionByMe_view(self):
        req = self.factory.get("/test/")
        req.user = self.user
        view = views.NotInCollectionByMe()
        view.setup(req)

        Note.objects.create(author=self.user)
        self.user.collected_notes.create(author=self.user)
        self.assertEqual(len(view.get_queryset()), 1)

        # Test for N+1 queries:
        for _ in range(3):
            Note.objects.create(author=self.user)
        self.client.login(username="juan", password="1234")
        with self.assertNumQueries(4):
            self.client.get(reverse("notes:not-in-collection-by-me"))

    def test_MyCollectionByOthers_view(self):
        req = self.factory.get("/test/")
        req.user = self.user
        view = views.MyCollectionByOthers()
        view.setup(req)

        user2 = UserModel.objects.create_user("user2", "user2@example.com", "1234")
        self.user.collected_notes.add(Note.objects.create(author=user2))
        self.user.collected_notes.add(Note.objects.create(author=self.user))
        self.assertEqual(len(view.get_queryset()), 1)

        # Test for N+1 queries:
        for _ in range(3):
            self.user.collected_notes.create(author=user2)
        self.client.login(username="juan", password="1234")
        with self.assertNumQueries(4):
            self.client.get(reverse("notes:my-collection-by-others"))

    def test_MyCollectionPromoted_view(self):
        req = self.factory.get("/test/")
        req.user = self.user
        view = views.MyCollectionPromoted()
        view.setup(req)

        self.user.collected_notes.add(Note.objects.create())
        note = Note.objects.create(author=self.user)
        self.user.collected_notes.add(note)
        Collection.objects.filter(user=self.user, note=note).update(promoted=True)
        self.assertEqual(len(view.get_queryset()), 1)

        # Test for N+1 queries:
        for _ in range(3):
            note = self.user.collected_notes.create(author=self.user)
            Collection.objects.filter(user=self.user, note=note).update(promoted=True)
        self.client.login(username="juan", password="1234")
        with self.assertNumQueries(4):
            self.client.get(reverse("notes:my-collection-promoted"))

    def test_SingleNote_view(self):
        note = Note.objects.create(author=self.user)
        res = self.client.get(reverse("notes:single-note", kwargs={"slug": note.code}))
        self.assertEqual(res.status_code, 200)

        self.client.login(username="juan", password="1234")
        res = self.client.get(reverse("notes:single-note", kwargs={"slug": note.code}))
        self.assertEqual(res.status_code, 200)

    def test_CollectionAction_action_kwarg(self):
        req = self.factory.post("/test/")
        req.user = self.user
        with self.assertRaises(ImproperlyConfigured):
            views.CollectionAction.as_view()(req, action="foobar")

    def test_CollectionAction_note404(self):
        self.client.login(username="juan", password="1234")
        res = self.client.post(
            reverse(
                "notes:collection-action", kwargs={"code": "FOOBAR", "action": "save"}
            )
        )
        self.assertEqual(res.status_code, 404)

    def test_CollectionAction_save(self):
        note = Note.objects.create()
        self.client.login(username="juan", password="1234")
        res = self.client.post(
            reverse(
                "notes:collection-action", kwargs={"code": note.code, "action": "save"}
            )
        )
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, note.get_absolute_url())
        self.assertEqual(self.user.collected_notes.all()[0].id, note.id)
        res = self.client.get(res.url)
        self.assertContains(res, "Note saved to collection")
        self.assertContains(
            res, f"<a href='{note.get_absolute_url()}'>View saved note</a>", html=True
        )

    def test_CollectionAction_unsave(self):
        note = Note.objects.create()
        self.user.collected_notes.add(note)
        self.assertEqual(self.user.collected_notes.all()[0].id, note.id)
        self.client.login(username="juan", password="1234")
        res = self.client.post(
            reverse(
                "notes:collection-action",
                kwargs={"code": note.code, "action": "unsave"},
            )
        )
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, note.get_absolute_url())
        self.assertEqual(self.user.collected_notes.count(), 0)
        res = self.client.get(res.url)
        self.assertContains(res, "Note removed from collection")
        self.assertContains(
            res, f"<a href='{note.get_absolute_url()}'>View removed note</a>", html=True
        )

    def test_CollectionAction_redirect_url(self):
        note = Note.objects.create()
        self.client.login(username="juan", password="1234")
        res = self.client.post(
            reverse(
                "notes:collection-action", kwargs={"code": note.code, "action": "save"}
            ),
            {"redirect_url": "/discover/"},
        )
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, "/discover/")

    def test_CollectionAction_redirect_url_is_note_absolute_url(self):
        note = Note.objects.create()
        self.client.login(username="juan", password="1234")
        res = self.client.post(
            reverse(
                "notes:collection-action", kwargs={"code": note.code, "action": "save"}
            ),
            {"redirect_url": note.get_absolute_url()},
            follow=True,
        )
        self.assertContains(res, "Note saved to collection")
        self.assertNotContains(res, "View saved note")

    # TODO: more views tests
