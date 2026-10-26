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

    return mark_safe(f'<script src="{LOADER_SRC}" data-key="{escape(key)}" async></script>')
