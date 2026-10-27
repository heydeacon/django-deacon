import json
import logging

from django import template
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.middleware.csrf import get_token
from django.urls import reverse
from django.utils.html import escape
from django.utils.safestring import mark_safe

from django_deacon import users

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

    nonce = _csp_nonce(context)

    return mark_safe(_signed_in_script(context, nonce) + _loader_tag(attributes, nonce))


def _signed_in_script(context, nonce):
    """
    Who is signed in, for the loader to read as it starts, so it goes above the loader tag. The
    token function asks the site's own POST /deacon/token to sign them when the chat opens,
    sending the CSRF token as every other POST on the site does. With nobody signed in it signs
    the visitor out, so a sign-out ends Deacon's proof of who they were. A request with no user
    to ask, without Django's AuthenticationMiddleware, gets neither.
    """
    request = getattr(context, "request", None) or context.get("request")
    user = getattr(request, "user", None)

    if user is None:
        return ""

    if not user.is_authenticated:
        return _script("window.deaconUser = null; window.Deacon?.identify(null);", nonce)

    return _script(
        f"window.deaconUser = {_user_object(request, user)}; "
        "window.Deacon?.identify(window.deaconUser);",
        nonce,
    )


def _user_object(request, user):
    """
    The user's id, email and name, and the token function: written as code rather than JSON,
    since a function has no JSON.
    """
    csrf_header = settings.CSRF_HEADER_NAME.removeprefix("HTTP_").replace("_", "-")
    headers = {"Content-Type": "application/json", csrf_header: get_token(request)}

    token = (
        "(nonce) => fetch("
        + _js(reverse("django_deacon:token"))
        + ', { method: "POST", credentials: "same-origin", headers: '
        + _js_object(headers)
        + ', body: JSON.stringify({ nonce }) }).then((r) => (r.status === 200 ? r.text() : ""))'
    )
    fields = [
        f"{name}: {_js(value)}" for name, value in users.details(user).items() if value is not None
    ]

    return "{ " + ", ".join([*fields, f"token: {token}"]) + " }"


# What a string can't hold inside a script without ending it or starting markup.
_SCRIPT_ESCAPES = {ord("<"): "\\u003C", ord(">"): "\\u003E", ord("&"): "\\u0026"}


def _js(value):
    """A string as JavaScript, escaped so nothing in it can end the script it sits in."""
    return json.dumps(str(value)).translate(_SCRIPT_ESCAPES)


def _js_object(values):
    return "{ " + ", ".join(f"{_js(name)}: {_js(value)}" for name, value in values.items()) + " }"


def _script(code, nonce):
    nonce_attribute = "" if nonce is None else f' nonce="{escape(nonce)}"'

    return f"<script{nonce_attribute}>{code}</script>"


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
