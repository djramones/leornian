"""Context processors for Leornian templates."""


def colormode(request):
    """Fetch theme color mode preference stored in a cookie."""
    mode = request.COOKIES.get("colormode")
    return {"colormode": mode}
