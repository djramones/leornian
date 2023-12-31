import formtools
import time
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone
from django.views.generic import ListView

from . import views
from .models import Collection, Deattribution, Note

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
            res = self.client.get(reverse("notes:my-collection"))
        self.assertEqual(res.status_code, 200)

    def test_MyCollection_view_template(self):
        """
        Test the MyCollection template, which uses request.resolver_match,
        through a view call.
        """
        self.client.login(username="juan", password="1234")
        res = self.client.get(reverse("notes:my-collection"))
        self.assertContains(
            res, '<a class="nav-link active" href="/collection/">All</a>', html=True
        )

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
            res = self.client.get(reverse("notes:my-collection-by-me"))
        self.assertEqual(res.status_code, 200)

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
            res = self.client.get(reverse("notes:not-in-collection-by-me"))
        self.assertEqual(res.status_code, 200)

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
            res = self.client.get(reverse("notes:my-collection-by-others"))
        self.assertEqual(res.status_code, 200)

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
            res = self.client.get(reverse("notes:my-collection-promoted"))
        self.assertEqual(res.status_code, 200)

    def test_SingleNote_view(self):
        note = Note.objects.create(author=self.user)

        # Unauthenticated:
        res = self.client.get(reverse("notes:single-note", kwargs={"slug": note.code}))
        self.assertEqual(res.status_code, 200)

        # Authenticated:
        self.client.login(username="juan", password="1234")
        res = self.client.get(reverse("notes:single-note", kwargs={"slug": note.code}))
        self.assertEqual(res.status_code, 200)

    def test_ChangeNoteVisibility_template(self):
        """Test template branches through view call."""
        self.client.login(username="juan", password="1234")
        note = Note.objects.create()

        # With blocker `not-author`:
        res = self.client.get(reverse("notes:change-vis", kwargs={"slug": note.code}))
        self.assertContains(res, "This note is not attributed to you")

        # With blocker `visibility-locked`:
        Note.objects.filter(pk=note.pk).update(author=self.user, visibility_locked=True)
        res = self.client.get(reverse("notes:change-vis", kwargs={"slug": note.code}))
        self.assertContains(res, "Its visibility attribute is locked")

        # With blocker and redirect_url
        res = self.client.get(
            reverse("notes:change-vis", kwargs={"slug": note.code}),
            {"redirect_url": "/0ef7b2d410f2bba1/"},
        )
        self.assertContains(
            res,
            '<a class="btn btn-secondary" href="/0ef7b2d410f2bba1/">OK</a>',
            html=True,
        )

        # Without blocker:
        Note.objects.filter(pk=note.pk).update(visibility_locked=False)
        res = self.client.get(
            reverse("notes:change-vis", kwargs={"slug": note.code}),
            {"redirect_url": "/0ef7b2d410f2bba1/"},
        )
        self.assertContains(res, '<i class="bi-check-circle"></i> Save')

    def test_ChangeNoteVisibility_get_queryset(self):
        note = Note.objects.create(author=self.user)
        self.client.login(username="juan", password="1234")
        with self.assertNumQueries(4):
            self.client.get(reverse("notes:change-vis", kwargs={"slug": note.code}))

    def test_ChangeNoteVisibility_blocker(self):
        note = Note.objects.create()
        req = self.factory.get("/test/")
        req.user = self.user
        view = views.ChangeNoteVisibility()
        view.setup(req, slug=note.code)
        self.assertEqual(view.blocker(), "not-author")

        Note.objects.filter(pk=note.pk).update(author=self.user, visibility_locked=True)
        self.assertEqual(view.blocker(), "visibility-locked")

        Note.objects.filter(pk=note.pk).update(visibility_locked=False)
        self.assertEqual(view.blocker(), None)

    def test_ChangeNoteVisibility_post(self):
        note = Note.objects.create(visibility=Note.Visibility.NORMAL)
        self.client.login(username="juan", password="1234")
        res = self.client.post(
            reverse("notes:change-vis", kwargs={"slug": note.code}),
            {"visibility": Note.Visibility.UNLISTED},
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            Note.objects.get(pk=note.pk).visibility, Note.Visibility.NORMAL
        )

        Note.objects.filter(pk=note.pk).update(author=self.user)
        res = self.client.post(
            reverse("notes:change-vis", kwargs={"slug": note.code}),
            {"visibility": Note.Visibility.UNLISTED},
        )
        self.assertEqual(res.status_code, 302)
        self.assertEqual(
            Note.objects.get(pk=note.pk).visibility, Note.Visibility.UNLISTED
        )

    def test_ChangeNoteVisibility_get_success_url(self):
        # No redirect_url supplied:
        note = Note.objects.create(author=self.user)
        self.client.login(username="juan", password="1234")
        res = self.client.post(
            reverse("notes:change-vis", kwargs={"slug": note.code}),
            {"visibility": Note.Visibility.UNLISTED},
        )
        self.assertEqual(res.url, note.get_absolute_url())

    def test_DeleteNote_confirm_delete_template(self):
        """Test template branches through view call."""
        self.client.login(username="juan", password="1234")
        note = Note.objects.create()

        # With blocker `not-author`:
        res = self.client.get(reverse("notes:delete-note", kwargs={"slug": note.code}))
        self.assertContains(res, "This note cannot be deleted")

        # With blocker `other-collectors`:
        Note.objects.filter(pk=note.pk).update(author=self.user)
        u2 = UserModel.objects.create_user("user2", "user2@example.com", "1234")
        u2.collected_notes.add(note)
        res = self.client.get(reverse("notes:delete-note", kwargs={"slug": note.code}))
        self.assertContains(res, "It is in the collection(s) of other user(s)")

        # Without blocker:
        u2.collected_notes.remove(note)
        res = self.client.get(reverse("notes:delete-note", kwargs={"slug": note.code}))
        self.assertContains(res, "Are you sure you want to delete the note below?")

    def test_DeleteNote_get_queryset(self):
        note = Note.objects.create(author=self.user)
        self.client.login(username="juan", password="1234")
        with self.assertNumQueries(5):
            self.client.get(reverse("notes:delete-note", kwargs={"slug": note.code}))

    def test_DeleteNote_blocker(self):
        note = Note.objects.create()
        req = self.factory.get("/test/")
        req.user = self.user
        view = views.DeleteNote()
        view.setup(req, slug=note.code)
        self.assertEqual(view.blocker(), "not-author")

        Note.objects.filter(pk=note.pk).update(author=self.user)
        user2 = UserModel.objects.create_user("user2", "user2@example.com", "1234")
        user2.collected_notes.add(note)
        self.assertEqual(view.blocker(), "other-collectors")

        user2.collected_notes.remove(note)
        self.assertEqual(view.blocker(), None)

    def test_DeleteNote_get_context_data(self):
        note = Note.objects.create()
        req = self.factory.get("/test/")
        req.user = self.user
        view = views.DeleteNote()
        view.setup(req, slug=note.code)
        view.object = view.get_object()  # normally done in view.get()
        self.assertEqual(view.get_context_data()["blocker"], "not-author")
        self.assertEqual(view.get_context_data()["redirect_url"], "")

    def test_DeleteNote_post(self):
        note = Note.objects.create()
        self.client.login(username="juan", password="1234")
        res = self.client.post(reverse("notes:delete-note", kwargs={"slug": note.code}))
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Note.objects.count(), 1)

        Note.objects.filter(pk=note.pk).update(author=self.user)
        res = self.client.post(reverse("notes:delete-note", kwargs={"slug": note.code}))
        self.assertEqual(res.status_code, 302)
        self.assertEqual(Note.objects.count(), 0)

    def test_DeleteNote_form_valid(self):
        note = Note.objects.create(author=self.user)
        self.client.login(username="juan", password="1234")
        res = self.client.post(
            reverse("notes:delete-note", kwargs={"slug": note.code}), follow=True
        )
        self.assertContains(res, "A note has been deleted")

    def test_DeleteNote_get_success_url(self):
        # No redirect_url supplied:
        note = Note.objects.create(author=self.user)
        self.client.login(username="juan", password="1234")
        res = self.client.post(reverse("notes:delete-note", kwargs={"slug": note.code}))
        self.assertEqual(res.url, reverse("notes:my-collection"))

        # redirect_url == Note.get_absolute_url():
        note = Note.objects.create(author=self.user)
        res = self.client.post(
            reverse(
                "notes:delete-note",
                kwargs={"slug": note.code},
            ),
            {"redirect_url": note.get_absolute_url()},
        )
        self.assertEqual(res.url, reverse("notes:my-collection"))

        # Normal case:
        note = Note.objects.create(author=self.user)
        res = self.client.post(
            reverse(
                "notes:delete-note",
                kwargs={"slug": note.code},
            ),
            {"redirect_url": "/foobar/"},
        )
        self.assertEqual(res.url, "/foobar/")

    def test_RemoveAttribution_get_queryset(self):
        note = Note.objects.create(author=self.user)
        self.client.login(username="juan", password="1234")
        with self.assertNumQueries(3):
            self.client.get(reverse("notes:deattribute", kwargs={"slug": note.code}))

    def test_RemoveAttribution_get(self):
        # Non-existent note
        res = self.client.get(reverse("notes:deattribute", kwargs={"slug": "FOOBAR"}))
        self.assertEqual(res.status_code, 404)

        # Unauthenticated, note has no author
        note = Note.objects.create()
        res = self.client.get(reverse("notes:deattribute", kwargs={"slug": note.code}))
        self.assertEqual(res.status_code, 403)

        # Authenticated, note still has no author
        self.client.login(username="juan", password="1234")
        res = self.client.get(reverse("notes:deattribute", kwargs={"slug": note.code}))
        self.assertEqual(res.status_code, 403)

        # Valid request
        Note.objects.filter(pk=note.pk).update(author=self.user)
        res = self.client.get(reverse("notes:deattribute", kwargs={"slug": note.code}))
        self.assertEqual(res.status_code, 200)

    def test_RemoveAttribution_post(self):
        # Non-existent note
        res = self.client.post(reverse("notes:deattribute", kwargs={"slug": "FOOBAR"}))
        self.assertEqual(res.status_code, 404)

        # Unauthenticated, note has no author
        note = Note.objects.create()
        res = self.client.post(reverse("notes:deattribute", kwargs={"slug": note.code}))
        self.assertEqual(res.status_code, 403)

        # Authenticated, note still has no author
        self.client.login(username="juan", password="1234")
        res = self.client.post(reverse("notes:deattribute", kwargs={"slug": note.code}))
        self.assertEqual(res.status_code, 403)

        # Valid request
        Note.objects.filter(pk=note.pk).update(author=self.user)
        res = self.client.post(
            reverse("notes:deattribute", kwargs={"slug": note.code}), follow=True
        )
        self.assertContains(res, "Attribution removed from note")
        self.assertContains(res, f"<a href='{reverse('notes:deattributed-notes')}'>")
        note = Note.objects.get(pk=note.pk)
        self.assertEqual(res.redirect_chain[0][0], note.get_absolute_url())
        self.assertEqual(note.author, None)
        self.assertEqual(Deattribution.objects.count(), 1)
        deatt = Deattribution.objects.all()[0]
        self.assertEqual(deatt.note.pk, note.pk)
        self.assertEqual(deatt.author, self.user)

    def test_RemoveAttribution_post_redirect_url(self):
        note = Note.objects.create(author=self.user)
        self.client.login(username="juan", password="1234")
        res = self.client.post(
            reverse("notes:deattribute", kwargs={"slug": note.code}),
            {"redirect_url": "/foo/bar/"},
            follow=True,
        )
        self.assertEqual(res.redirect_chain[0][0], "/foo/bar/")

    def test_RestoreAttribution(self):
        # Unathenticated
        note = Note.objects.create()
        res = self.client.post(reverse("notes:reattribute", kwargs={"slug": note.code}))
        self.assertEqual(res.status_code, 403)

        # Non-existent note code
        self.client.login(username="juan", password="1234")
        res = self.client.post(reverse("notes:reattribute", kwargs={"slug": "FOOBAR"}))
        self.assertEqual(res.status_code, 404)

        # No deattribution record
        res = self.client.post(reverse("notes:reattribute", kwargs={"slug": note.code}))
        self.assertEqual(res.status_code, 400)

        # Valid request
        Deattribution.objects.create(note=note, author=self.user)
        res = self.client.post(
            reverse("notes:reattribute", kwargs={"slug": note.code}), follow=True
        )
        self.assertContains(
            res, f"attribution restored. <a href='{note.get_absolute_url()}'>"
        )
        self.assertEqual(Note.objects.get(pk=note.pk).author, self.user)
        self.assertEqual(Deattribution.objects.count(), 0)

    def test_DeattributedNotes_get_queryset(self):
        req = self.factory.get("/test/")
        req.user = self.user
        view = views.DeattributedNotes()
        view.setup(req)

        for _ in range(3):
            note = Note.objects.create()
            Deattribution.objects.create(note=note, author=self.user)
        u2 = UserModel.objects.create_user("user2", "user2@example.com", "1234")
        Deattribution.objects.create(note=Note.objects.create(), author=u2)
        self.assertEqual(len(view.get_queryset()), 3)

        # Test for N+1 queries:
        self.client.login(username="juan", password="1234")
        with self.assertNumQueries(4):
            res = self.client.get(reverse("notes:deattributed-notes"))
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

    def test_Discover_get_unauthenticated(self):
        Note.objects.create(text="86b337cf632a2c99")
        # With only one note, fetching is deterministic.
        res = self.client.get(reverse("notes:discover"))
        self.assertContains(res, "86b337cf632a2c99")

    def test_Discover_get_authenticated(self):
        self.user.collected_notes.create(text="d9b3ff70ef1682d3")
        # With only one note, fetching is deterministic.
        self.client.login(username="juan", password="1234")
        res = self.client.get(reverse("notes:discover"))
        self.assertNotContains(res, "d9b3ff70ef1682d3")

    def test_Discover_post_unauthenticated(self):
        note = Note.objects.create()
        res = self.client.post(reverse("notes:discover"), {"code": note.code})
        self.assertEqual(res.status_code, 403)

    def test_Discover_post_authenticated(self):
        note = Note.objects.create()
        self.client.login(username="juan", password="1234")
        self.assertEqual(self.user.collected_notes.count(), 0)
        res = self.client.post(reverse("notes:discover"), {"code": note.code})
        self.assertEqual(res.status_code, 302)
        self.assertEqual(self.user.collected_notes.count(), 1)
        self.assertEqual(self.user.collected_notes.all()[0].id, note.id)
        self.assertEqual(res.url, reverse("notes:discover"))
        res = self.client.get(res.url)
        self.assertContains(res, "A note has been saved to your collection.")
        self.assertContains(
            res, f" <a href='{note.get_absolute_url()}'>View saved note</a>", html=True
        )

    def test_Drill_unauthenticated(self):
        res = self.client.get(reverse("notes:drill"))
        self.assertEqual(res.status_code, 302)
        res = self.client.post(reverse("notes:drill"))
        self.assertEqual(res.status_code, 302)

    def test_Drill_get(self):
        self.client.login(username="juan", password="1234")
        res = self.client.get(reverse("notes:drill"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context["disable_begin"], True)
        self.assertEqual(res.context["recent_drill_count"], 0)

        self.user.collected_notes.create()  # first collection record
        note = Note.objects.create()
        Collection.objects.create(
            user=self.user,
            note=note,
            last_drilled=timezone.now() - timezone.timedelta(hours=25),
        )  # second collection record
        res = self.client.get(reverse("notes:drill"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context["disable_begin"], False)
        self.assertEqual(res.context["recent_drill_count"], 1)

    def test_Drill_generate_weights(self):
        self.assertEqual(views.Drill.generate_weights([]), [])
        self.assertEqual(
            views.Drill.generate_weights([False, True, False]),
            [0.061728395061728385, 3.333333333333333, 5.0],
        )
        self.assertEqual(
            views.Drill.generate_weights([True, False, True, False, False, True]),
            [
                0.8333333333333333,
                0.061728395061728385,
                2.5,
                0.9876543209876542,
                2.411265432098766,
                5.0,
            ],
        )

    def test_Drill_promote(self):
        self.client.login(username="juan", password="1234")
        note = Note.objects.create()
        self.user.collected_notes.add(note)
        self.assertEqual(
            Collection.objects.get(note=note, user=self.user).promoted, False
        )
        res = self.client.post(reverse("notes:drill"), {"promote": note.code})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            Collection.objects.get(note=note, user=self.user).promoted, True
        )

    def test_Drill_demote(self):
        self.client.login(username="juan", password="1234")
        note = Note.objects.create()
        self.user.collected_notes.add(note)
        Collection.objects.filter(note=note, user=self.user).update(promoted=True)
        res = self.client.post(reverse("notes:drill"), {"demote": note.code})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            Collection.objects.get(note=note, user=self.user).promoted, False
        )

    def test_Drill_invalid_promote_code(self):
        self.client.login(username="juan", password="1234")
        res = self.client.post(reverse("notes:drill"), {"promote": "foo1234"})
        self.assertNotContains(res, "A note has been promoted")

    def test_Drill_invalid_demote_code(self):
        self.client.login(username="juan", password="1234")
        res = self.client.post(reverse("notes:drill"), {"demote": "foo1234"})
        self.assertNotContains(res, "A note has been demoted")

    def test_Drill_insufficient_collection(self):
        self.client.login(username="juan", password="1234")
        res = self.client.post(reverse("notes:drill"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context["error"], "insufficient-collection")

    def test_Drill_draw(self):
        self.client.login(username="juan", password="1234")
        # Add one note to collection...
        note_old = Note.objects.create()
        self.user.collected_notes.add(note_old)
        Collection.objects.filter(note=note_old, user=self.user).update(promoted=True)
        note_old_pre_last_drilled = Collection.objects.get(
            note=note_old, user=self.user
        ).last_drilled
        # ...and then add another:
        time.sleep(0.001)  # just to ensure that the timestamps increment
        note_new = Note.objects.create()
        self.user.collected_notes.add(note_new)
        note_new_pre_last_drilled = Collection.objects.get(
            note=note_new, user=self.user
        ).last_drilled
        # With just two notes, the drill draw is deterministic:
        res = self.client.post(reverse("notes:drill"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context["note"].id, note_old.id)
        self.assertEqual(res.context["promoted"], True)
        self.assertEqual(res.context["recent_drill_count"], 2)
        note_old_post_last_drilled = Collection.objects.get(
            note=note_old, user=self.user
        ).last_drilled
        note_new_post_last_drilled = Collection.objects.get(
            note=note_new, user=self.user
        ).last_drilled
        self.assertGreater(note_old_post_last_drilled, note_old_pre_last_drilled)
        self.assertEqual(note_new_post_last_drilled, note_new_pre_last_drilled)

    def test_Start_view(self):
        req = self.factory.get("/test/")
        res = views.Start.as_view()(req)
        self.assertEqual(res.status_code, 200)
