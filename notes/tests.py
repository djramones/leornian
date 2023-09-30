from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from .models import Note

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
