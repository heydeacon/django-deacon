import json
import logging

from django import template
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()
logger = logging.getLogger("django_deacon")

LOADER_SRC = "https://heydeacon.com/widget/v1/loader.js"

MISSING_KEY = (
    "django-deacon: the DEACON_KEY setting is missing, so the page has no Deacon widget. In "
    "Deacon, open Install (the button at the top of the dashboard) and copy the data-key value "
    "from the snippet. It starts with pk_."
)


@register.simple_tag(takes_context=True)
def deacon_widget(context):
    """
    The tag Install gives, with the key from the DEACON_KEY setting. With no key it prints
    nothing and logs a warning, so a missing setting never takes a page down.
    """
    key = str(getattr(settings, "DEACON_KEY", None) or "").strip()

    if key == "":
        logger.warning(MISSING_KEY)
        return ""

    deacon_context = getattr(settings, "DEACON_CONTEXT", None)
    page_views = getattr(settings, "DEACON_PAGE_VIEWS", True)
    _check_context(deacon_context)
    _check_page_views(page_views)

    attributes = {"data-key": key}
    if deacon_context is not None:
        attributes["data-context"] = json.dumps(
            deacon_context, separators=(",", ":"), ensure_ascii=False
        )
    if page_views is False:
        attributes["data-no-page-views"] = True

    return _loader_tag(attributes, _csp_nonce(context))


def _csp_nonce(context):
    """
    The request's Content Security Policy nonce: from Django's own CSP support (6.0 and
    later, through its csp context processor), else from django-csp's request.csp_nonce, or
    None when the project has no nonce.
    """
    nonce = context.get("csp_nonce")
    if nonce is None:
        nonce = getattr(context.get("request"), "csp_nonce", None)

    return None if nonce is None else str(nonce)


def _check_context(deacon_context):
    """A wrong type is a mistake in the project's settings, so it raises."""
    if deacon_context is None:
        return

    if not isinstance(deacon_context, dict) or not all(
        isinstance(value, str | int | float | bool) for value in deacon_context.values()
    ):
        raise ImproperlyConfigured(
            "django-deacon: the DEACON_CONTEXT setting must be a dict whose values are strings, "
            "numbers or booleans."
        )


def _check_page_views(page_views):
    if not isinstance(page_views, bool):
        raise ImproperlyConfigured(
            "django-deacon: the DEACON_PAGE_VIEWS setting must be True or False."
        )


def _loader_tag(attributes, nonce):
    """
    The tag Install gives, with any of its other attributes between the key and async, and
    the nonce after them. An attribute that is True is written with no value, as async is.
    """
    rendered = "".join(
        f" {name}" if value is True else f' {name}="{escape(value)}"'
        for name, value in attributes.items()
    )

    nonce_attribute = "" if nonce is None else f' nonce="{escape(nonce)}"'

    return mark_safe(f'<script src="{LOADER_SRC}"{rendered} async{nonce_attribute}></script>')
