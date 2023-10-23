from django.contrib.sites.shortcuts import get_current_site


def get_object_url(request, obj):
    """Get the complete URL for an object, including the scheme and domain."""
    url = "https" if request.is_secure() else "http"
    url += "://" + str(get_current_site(request))
    url += obj.get_absolute_url()
    return url
