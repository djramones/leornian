from django.contrib import messages
from django.http import HttpResponseRedirect


def messages_test(request):
    """
    Add some dummy messages and then redirect to the root URL. Intended for
    development only.
    """
    test_messages = [
        (messages.INFO, "Lorem ipsum dolor, sit amet consectetum."),
        (messages.WARNING, "Oops! Here's a fake warning."),
        (messages.INFO, "Foo bar."),
    ]
    for tag, msg in test_messages:
        messages.add_message(request, tag, msg)
    return HttpResponseRedirect("/")
