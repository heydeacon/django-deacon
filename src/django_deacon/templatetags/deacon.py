import json
import logging

from django import template
from django.conf import settings
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

    attributes = {"data-key": key}
    if deacon_context is not None:
        attributes["data-context"] = json.dumps(
            deacon_context, separators=(",", ":"), ensure_ascii=False
        )

    return loader_tag(attributes)


def loader_tag(attributes):
    """The tag Install gives, with any of its other attributes between the key and async."""
    rendered = "".join(f' {name}="{escape(value)}"' for name, value in attributes.items())

    return mark_safe(f'<script src="{LOADER_SRC}"{rendered} async></script>')
