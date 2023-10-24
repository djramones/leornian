from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError
from django.template import Context, Template
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse, resolve, Resolver404
from django.utils import timezone

from .models import Collection, Deattribution, Note
from .utils import generate_lorem_ipsum, generate_reference_code

UserModel = get_user_model()


class BasicTests(TestCase):
    def setUp(self):
        self.note = Note.objects.create()
        self.user = UserModel.objects.create_user("juan", "juan@example.com", "1234")

    def test_basic_requests_unauthenticated(self):
        response = self.client.get(reverse("notes:create-note"))
        self.assertEqual(response.status_code, 302)
        response = self.client.get(
            reverse("notes:change-vis", kwargs={"slug": self.note.code})
        )
        self.assertEqual(response.status_code, 302)
        response = self.client.get(
            reverse("notes:delete-note", kwargs={"slug": self.note.code})
        )
        self.assertEqual(response.status_code, 302)
        response = self.client.get(
            reverse("notes:deattribute", kwargs={"slug": self.note.code})
        )
        self.assertEqual(response.status_code, 403)
        response = self.client.get(
            reverse("notes:reattribute", kwargs={"slug": self.note.code})
        )
        self.assertEqual(response.status_code, 405)
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
        response = self.client.get(reverse("notes:deattributed-notes"))
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
        response = self.client.get(
            reverse("notes:change-vis", kwargs={"slug": self.note.code})
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse("notes:delete-note", kwargs={"slug": self.note.code})
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse("notes:deattribute", kwargs={"slug": self.note.code})
        )
        self.assertEqual(response.status_code, 403)
        response = self.client.get(
            reverse("notes:reattribute", kwargs={"slug": self.note.code})
        )
        self.assertEqual(response.status_code, 405)
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
        response = self.client.get(reverse("notes:deattributed-notes"))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse("notes:notes-by-username", kwargs={"username": self.user.username})
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("notes:discover"))
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
        response = self.client.get(
            reverse("notes:single-note", kwargs={"slug": self.note.code})
        )
        self.assertEqual(response.status_code, 200)


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

    def test_deattribution_unique_note(self):
        note = Note.objects.create()
        u1 = UserModel.objects.create_user("mary", "mary@example.com", "1234")
        Deattribution.objects.create(note=note, author=u1)
        u2 = UserModel.objects.create_user("juan", "juan@example.com", "1234")
        with self.assertRaises(IntegrityError):
            Deattribution.objects.create(note=note, author=u2)


class CommandRemoveOldDeattributionsTests(TestCase):
    def setUp(self):
        user = UserModel.objects.create_user("x", "x@example.com", "1234")
        Deattribution.objects.create(note=Note.objects.create(), author=user)
        deatt = Deattribution.objects.create(note=Note.objects.create(), author=user)
        Deattribution.objects.filter(pk=deatt.pk).update(
            created=timezone.now() - timezone.timedelta(days=5)
        )

    def test_invalid_num_days(self):
        with self.assertRaises(CommandError):
            call_command("remove_old_deattributions", "0")

    def test_no_records_for_deletion(self):
        out = StringIO()
        call_command("remove_old_deattributions", "10", stdout=out)
        self.assertIn("0 record(s)", out.getvalue())
        self.assertEqual(Deattribution.objects.count(), 2)

    def test_deletion(self):
        out = StringIO()
        call_command("remove_old_deattributions", "1", stdout=out)
        self.assertIn("1 record(s)", out.getvalue())
        self.assertEqual(Deattribution.objects.count(), 1)


class TemplatesTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_my_collection_html(self):
        req = self.factory.get("/test/")

        # notes:my-collection
        req.resolver_match = resolve(reverse("notes:my-collection"))
        out = render_to_string("notes/my-collection.html", {"request": req})
        self.assertInHTML('<a class="nav-link active" href="/collection/">All</a>', out)

        # notes:my-collection-by-me
        req.resolver_match = resolve(reverse("notes:my-collection-by-me"))
        out = render_to_string("notes/my-collection.html", {"request": req})
        self.assertInHTML(
            '<a class="nav-link active" href="/collection/by-me/">By Me</a>', out
        )

        # notes:not-in-collection-by-me
        req.resolver_match = resolve(reverse("notes:not-in-collection-by-me"))
        out = render_to_string("notes/my-collection.html", {"request": req})
        self.assertInHTML(
            '<a class="nav-link" href="/collection/by-me/">By Me</a>', out
        )
        self.assertInHTML(
            '<div class="alert alert-info text-center">These notes are authored by you but are <strong><em>not saved in your collection</em></strong>.</div>',
            out,
        )

        # notes:my-collection-by-others
        req.resolver_match = resolve(reverse("notes:my-collection-by-others"))
        out = render_to_string("notes/my-collection.html", {"request": req})
        self.assertInHTML(
            '<a class="nav-link active" href="/collection/by-others/">By Others</a>',
            out,
        )

        # notes:my-collection-promoted
        req.resolver_match = resolve(reverse("notes:my-collection-promoted"))
        out = render_to_string("notes/my-collection.html", {"request": req})
        self.assertInHTML(
            f'<div class="alert alert-secondary text-center">These are the notes in your collection that are promoted in <a href="{reverse("notes:drill")}">Drill</a>.</div>',
            out,
        )


class NoteControlsTemplateTagTests(TestCase):
    def setUp(self):
        self.note = Note.objects.create()
        self.user = UserModel.objects.create_user("juan", "juan@example.com", "1234")
        self.request = RequestFactory().get("/test-9ebb5a63/")

    def test_note_controls_unauthenticated(self):
        self.note.saved = False
        self.request.user = AnonymousUser()
        out = Template(
            "{% load note_controls %}{% note_controls note request %}"
        ).render(Context({"note": self.note, "request": self.request}))
        self.assertHTMLEqual(out, '<div class="d-flex flex-wrap gap-2 column-gap-3">')

    def test_note_controls_authenticated_saved(self):
        self.note.saved = True
        self.request.user = self.user
        out = Template(
            "{% load note_controls %}{% note_controls note request %}"
        ).render(Context({"note": self.note, "request": self.request}))
        self.assertIn("Unsave", out)
        self.assertIn("/test-9ebb5a63/", out)
        self.assertNotIn("Save", out)
        self.assertIn("Report Content", out)

    def test_note_controls_authenticated_unsaved(self):
        self.note.saved = False
        self.request.user = self.user
        out = Template(
            "{% load note_controls %}{% note_controls note request %}"
        ).render(Context({"note": self.note, "request": self.request}))
        self.assertIn("Save", out)
        self.assertIn("/test-9ebb5a63/", out)
        self.assertNotIn("Unsave", out)
        self.assertIn("Report Content", out)

    def test_note_controls_authenticated_user_is_note_author(self):
        Note.objects.filter(pk=self.note.pk).update(author=self.user)
        self.note = Note.objects.get(pk=self.note.pk)  # reload from DB
        self.note.saved = True
        self.request.user = self.user
        out = Template(
            "{% load note_controls %}{% note_controls note request %}"
        ).render(Context({"note": self.note, "request": self.request}))
        self.assertIn("Change Visibility", out)
        self.assertIn("Delete", out)
        self.assertIn("Remove Attribution", out)
        self.assertIn("/test-9ebb5a63/", out)


class NoteExtrasTemplateTagTests(TestCase):
    def test_note_vis_badge(self):
        note = Note.objects.create(visibility=Note.Visibility.NORMAL)
        label = note.get_visibility_display()
        out = Template("{% load note_extras %}{% note_vis_badge note %}").render(
            Context({"note": note})
        )
        self.assertHTMLEqual(
            out,
            f'<span class="badge text-bg-success"><i class="bi-eye"></i>{label}</span>',
        )


@override_settings(ROOT_URLCONF="notes.urls")
class URLsTests(TestCase):
    def test_urls(self):
        self.assertEqual(resolve("/@foobar/").view_name, "notes-by-username")
        self.assertEqual(resolve("/foobar/save/").view_name, "collection-action")
        self.assertEqual(resolve("/foobar/unsave/").view_name, "collection-action")
        with self.assertRaises(Resolver404):
            resolve("/foobar/buzz/")
        self.assertEqual(resolve("/foobar/").view_name, "single-note")


class UtilsTests(TestCase):
    def test_generate_reference_code(self):
        code = generate_reference_code()
        self.assertRegex(code, "[0-9A-Z]{9}")

    def test_generate_lorem_ipsum(self):
        text = generate_lorem_ipsum()
        self.assertEqual(text[:5], "Lorem")
        generate_lorem_ipsum(rich=True)
