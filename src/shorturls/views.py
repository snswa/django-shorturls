import urlparse
from django.conf import settings
from django.contrib.sites.models import Site, RequestSite
from django.db import models
from django.http import HttpResponsePermanentRedirect, Http404
from django.shortcuts import get_object_or_404
from shorturls.baseconv import base62

def redirect(request, prefix, tiny):
    """
    Redirect to a given object from a short URL.
    """
    # Resolve the prefix and encoded ID into a model object and decoded ID.
    # Many things here could go wrong -- bad prefix, bad value in 
    # SHORTEN_MODELS, no such model, bad encoding -- so just return a 404 if
    # any of that stuff goes wrong.
    try:
        app_label, model_name = settings.SHORTEN_MODELS[prefix].split('.')
        model = models.get_model(app_label, model_name)
        if not model: raise ValueError
        id = base62.to_decimal(tiny)
    except (AttributeError, ValueError, KeyError):
        raise Http404('Bad prefix, model, SHORTEN_MODELS, or encoded ID.')
    
    # Try to look up the object. If it's not a valid object, or if it doesn't
    # have an absolute url, bail again.
    obj = get_object_or_404(model, pk=id)
    try:
        url = obj.get_absolute_url()
    except AttributeError:
        raise Http404("'%s' models don't have a get_absolute_url() method." % model.__name__)
    
    # We might have to translate the URL -- the badly-named get_absolute_url
    # actually returns a domain-relative URL -- into a fully qualified one.
    
    # If we got a fully-qualified URL, sweet.
    if urlparse.urlsplit(url)[0]:
        get = request.GET.urlencode()
        if get:
            url = '{0}?{1}'.format(url, get)
        return HttpResponsePermanentRedirect(url)
    
    # Otherwise, we need to make a full URL by prepending a base URL.
    # First, look for an explicit setting.
    if hasattr(settings, 'SHORTEN_FULL_BASE_URL') and settings.SHORTEN_FULL_BASE_URL:
        base = settings.SHORTEN_FULL_BASE_URL
        
    # Next, if the sites app is enabled, redirect to the current site.
    elif Site._meta.installed:
        base = 'http://%s/' % Site.objects.get_current().domain
        
    # Finally, fall back on the current request.
    else:
        base = 'http://%s/' % RequestSite(request).domain

    url = urlparse.urljoin(base, url)
    get = request.GET.urlencode()
    if get:
        url = '{0}?{1}'.format(url, get)
    return HttpResponsePermanentRedirect(url)