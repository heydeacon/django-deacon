from django import template
from django.conf import settings
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

LOADER_SRC = "https://heydeacon.com/widget/v1/loader.js"


@register.simple_tag(takes_context=True)
def deacon_widget(context):
    """The tag Install gives, with the key from the DEACON_KEY setting."""
    key = getattr(settings, "DEACON_KEY", None)

    return mark_safe(f'<script src="{LOADER_SRC}" data-key="{escape(key)}" async></script>')
