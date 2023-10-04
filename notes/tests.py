from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError
from django.http import Http404
from django.test import TestCase, RequestFactory
from django.views.generic import ListView
from django.urls import reverse
import formtools

from .models import Collection, Note
from .utils import generate_lorem_ipsum, generate_reference_code
from . import views

UserModel = get_user_model()


class BasicTests(TestCase):
    def setUp(self):
        self.note = Note.objects.create()
        self.user = UserModel.objects.create_user("juan", "juan@example.com", "1234")

    def test_basic_requests_unauthenticated(self):
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
        response = self.client.get(reverse("notes:my-collection-promoted"))
        self.assertEqual(response.status_code, 302)
        response = self.client.get(
            reverse("notes:notes-by-username", kwargs={"username": self.user.username})
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("notes:discover"))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("notes:drill"))
        self.assertEqual(response.status_code, 302)
        response = self.client.get(
            reverse(
                "notes:collection-action",
                kwargs={"code": self.note.code, "action": "save"},
            )
        )
        self.assertEqual(response.status_code, 302)
        response = self.client.get(
            reverse(
                "notes:collection-action",
                kwargs={"code": self.note.code, "action": "unsave"},
            )
        )
        self.assertEqual(response.status_code, 302)
        response = self.client.get(
            reverse("notes:single-note", kwargs={"slug": self.note.code})
        )
        self.assertEqual(response.status_code, 200)

    def test_basic_requests_authenticated(self):
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
        response = self.client.get(reverse("notes:my-collection-promoted"))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("notes:drill"))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse(
                "notes:collection-action",
                kwargs={"code": self.note.code, "action": "save"},
            )
        )
        self.assertEqual(response.status_code, 405)
        response = self.client.post(
            reverse(
                "notes:collection-action",
                kwargs={"code": self.note.code, "action": "save"},
            )
        )
        self.assertEqual(response.status_code, 302)
        response = self.client.get(
            reverse(
                "notes:collection-action",
                kwargs={"code": self.note.code, "action": "unsave"},
            )
        )
        self.assertEqual(response.status_code, 405)
        response = self.client.post(
            reverse(
                "notes:collection-action",
                kwargs={"code": self.note.code, "action": "unsave"},
            )
        )
        self.assertEqual(response.status_code, 302)


SAFE_MARKDOWN_INPUT = """Emphasis: *italic with asterisks*, **bold with asterisks**, ***italic and bold with asterisks***; _italic with underscores_, __bold with underscores__, ___italic and bold with underscores___.

~~Strikethrough with tildes~~.

Inline code with backticks: `os.urandom(16)`.

HTML entities: &mdash;, &ndash;, &copy;.

Backslash escapes: \\*asterisk emphasis*, \\_underscore emphasis_, HTML entity: \\&mdash;.

- Unordered list
- Foo
    - Indented list item
- Bar

1. Ordered list
2. Second item"""

DISALLOWED_MARKDOWN_INPUT = """Disallowed Markdown input

<pre>An HTML block.</pre>

    # indented code block
    import random
    random.random()

```
# fenced code block
import uuid
uuid.uuid4()
```

> This is a blockquote.

# An ATX heading

## A smaller ATX heading

A setext heading
=========

A smaller setext heading
---------

[A link](https://reversedelay.net/)

An autolink: <https://reversedelay.net/>

![Image](https://reversedelay.files.wordpress.com/2023/08/bike.jpg)"""


class ModelsTests(TestCase):
    def test_notequeryset_annotate_for_controls(self):
        user = UserModel.objects.create_user("juan", "juan@example.com", "1234")
        note = Note.objects.create()

        qs = Note.objects.annotate_for_controls(AnonymousUser())
        with self.assertRaises(AttributeError):
            qs[0].saved

        qs = Note.objects.annotate_for_controls(user)
        self.assertFalse(qs[0].saved)

        user.collected_notes.add(note)
        qs = Note.objects.annotate_for_controls(user)
        self.assertTrue(qs[0].saved)

    def test_notequeryset_get_random(self):
        """
        Test get_random()

        We create one note at a time only to get deterministic results.
        """
        user = UserModel.objects.create_user("juan", "juan@example.com", "1234")

        # Default case
        note = Note.objects.create()
        fetched_note = Note.objects.get_random()
        self.assertEqual(note.id, fetched_note.id)
        note.delete()

        # Exclude unlisted notes
        note = Note.objects.create(visibility=Note.Visibility.UNLISTED)
        self.assertEqual(Note.objects.get_random(), None)
        note.delete()

        # Exclude collected by user
        note = Note.objects.create()
        user.collected_notes.add(note)
        self.assertEqual(Note.objects.get_random(user), None)
        self.assertEqual(Note.objects.get_random().id, note.id)
        note.delete()

        # Exclude authored by user
        note = Note.objects.create(author=user)
        self.assertEqual(Note.objects.get_random(user), None)
        self.assertEqual(Note.objects.get_random().id, note.id)
        note.delete()

    def test_note_author_on_delete(self):
        user = UserModel.objects.create_user("juan", "juan@example.com", "1234")
        note = Note.objects.create(author=user)
        self.assertEqual(UserModel.objects.count(), 1)
        self.assertEqual(Note.objects.count(), 1)
        self.assertEqual(note.author, user)
        user.delete()
        self.assertEqual(UserModel.objects.count(), 0)
        self.assertEqual(Note.objects.count(), 1)
        # Need to reload the object from DB to see on_delete effect:
        self.assertEqual(Note.objects.get(id=note.id).author, None)

    def test_note_safe_markdown_rendering(self):
        note = Note.objects.create(text=SAFE_MARKDOWN_INPUT)
        html = note.html
        self.assertInHTML("<em>italic with asterisks</em>", html)
        self.assertInHTML("<strong>bold with asterisks</strong>", html)
        self.assertInHTML(
            "<em><strong>italic and bold with asterisks</strong></em>", html
        )
        self.assertInHTML("<em>italic with underscores</em>", html)
        self.assertInHTML("<strong>bold with underscores</strong>", html)
        self.assertInHTML(
            "<em><strong>italic and bold with underscores</strong></em>", html
        )
        self.assertInHTML("<s>Strikethrough with tildes</s>", html)
        self.assertInHTML("<code>os.urandom(16)</code>", html)
        self.assertInHTML("<p>HTML entities: —, –, ©.</p>", html)
        self.assertInHTML(
            "<p>Backslash escapes: *asterisk emphasis*, _underscore emphasis_, HTML entity: &amp;mdash;.</p>",
            html,
        )
        self.assertInHTML(
            "<ul><li>Unordered list</li><li>Foo<ul><li>Indented list item</li></ul></li><li>Bar</li></ul>",
            html,
        )
        self.assertInHTML("<ol><li>Ordered list</li><li>Second item</li></ol>", html)

    def test_note_disallowed_markdown_rendering(self):
        note = Note.objects.create(text=DISALLOWED_MARKDOWN_INPUT)
        html = note.html
        self.assertInHTML("&lt;pre&gt;An HTML block.&lt;/pre&gt;", html)
        self.assertInHTML(
            "<p># indented code block import random random.random()</p>", html
        )
        self.assertInHTML(
            "<p><code># fenced code block import uuid uuid.uuid4()</code></p>", html
        )
        self.assertInHTML("<p>&gt; This is a blockquote.</p>", html)
        self.assertInHTML("<p># An ATX heading</p>", html)
        self.assertInHTML("<p>## A smaller ATX heading</p>", html)
        self.assertInHTML("<p>A setext heading =========</p>", html)
        self.assertInHTML("<p>A smaller setext heading ---------</p>", html)
        self.assertInHTML("<p>[A link](https://reversedelay.net/)</p>", html)
        self.assertInHTML("<p>An autolink: &lt;https://reversedelay.net/&gt;</p>", html)
        self.assertInHTML(
            "<p>![Image](https://reversedelay.files.wordpress.com/2023/08/bike.jpg)</p>",
            html,
        )

    def test_note_default_ordering(self):
        Note.objects.create(text="first")
        Note.objects.create(text="second")
        self.assertEqual(Note.objects.all()[0].text, "second")
        self.assertEqual(Note.objects.all()[1].text, "first")

    def test_note_str(self):
        """Test Note.__str__()"""
        note = Note.objects.create()
        self.assertEqual(str(note), note.code)

    def test_collection_on_delete(self):
        user = UserModel.objects.create_user("juan", "juan@example.com", "1234")
        note = Note.objects.create()
        user.collected_notes.add(note)
        self.assertEqual(UserModel.objects.count(), 1)
        self.assertEqual(Note.objects.count(), 1)
        self.assertEqual(Collection.objects.count(), 1)

        # Case: deleting note
        note.delete()
        self.assertEqual(UserModel.objects.count(), 1)
        self.assertEqual(Note.objects.count(), 0)
        self.assertEqual(Collection.objects.count(), 0)

        # Replace note
        user.collected_notes.add(Note.objects.create())
        self.assertEqual(Collection.objects.count(), 1)

        # Case: deleting user
        user.delete()
        self.assertEqual(UserModel.objects.count(), 0)
        self.assertEqual(Note.objects.count(), 1)
        self.assertEqual(Collection.objects.count(), 0)

    def test_collection_unique_collect_constraint(self):
        user = UserModel.objects.create_user("juan", "juan@example.com", "1234")

        note = Note.objects.create()
        user.collected_notes.add(note)
        # Add again, should not create new collection record:
        user.collected_notes.add(note)
        self.assertEqual(Collection.objects.count(), 1)
        self.assertEqual(user.collected_notes.count(), 1)

        # Directly with Collection.objects.create():
        with self.assertRaises(IntegrityError):
            Collection.objects.create(user=user, note=note)


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

    # TODO: more views tests


# TODO: TemplatesTests
# TODO: TemplateTagsTests
# TODO: URLsTests


class UtilsTests(TestCase):
    def test_generate_reference_code(self):
        code = generate_reference_code()
        self.assertRegex(code, "[0-9A-Z]{8}")

    def test_generate_lorem_ipsum(self):
        text = generate_lorem_ipsum()
        self.assertEqual(text[:5], "Lorem")
        generate_lorem_ipsum(rich=True)
