import logging
from html.parser import HTMLParser

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.template import Context, Template


def render_widget(request, **variables):
    """What a base template's {% deacon_widget %} prints for this request."""
    template = Template("{% load deacon %}{% deacon_widget %}")
    return template.render(Context({"request": request, **variables}))


def script_attributes(html):
    """The attributes of the first script tag in some HTML, as a browser reads them."""
    found = []

    class Parser(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag == "script" and not found:
                found.append(dict(attrs))

    Parser().feed(html)
    return found[0]


def test_prints_the_tag_from_install_with_the_key_from_the_deacon_key_setting(settings, rf):
    settings.DEACON_KEY = "pk_test123"

    assert render_widget(rf.get("/")) == (
        '<script src="https://heydeacon.com/widget/v1/loader.js" data-key="pk_test123" async>'
        "</script>"
    )


def test_trims_spaces_pasted_around_the_key(settings, rf):
    settings.DEACON_KEY = "  pk_test123\n"

    assert render_widget(rf.get("/")) == (
        '<script src="https://heydeacon.com/widget/v1/loader.js" data-key="pk_test123" async>'
        "</script>"
    )


MISSING_KEY = (
    "django-deacon: the DEACON_KEY setting is missing, so the page has no Deacon widget. In "
    "Deacon, open Install (the button at the top of the dashboard) and copy the data-key value "
    "from the snippet. It starts with pk_."
)


@pytest.mark.parametrize(
    "key",
    [
        pytest.param(None, id="unset"),
        pytest.param("", id="empty, as from an unset environment variable"),
        pytest.param("   ", id="blank"),
    ],
)
def test_prints_nothing_and_logs_a_warning_when_the_key_is_missing(settings, rf, caplog, key):
    if key is None:
        del settings.DEACON_KEY
    else:
        settings.DEACON_KEY = key

    with caplog.at_level(logging.WARNING, logger="django_deacon"):
        rendered = render_widget(rf.get("/"))

    assert (rendered, caplog.record_tuples) == (
        "",
        [("django_deacon", logging.WARNING, MISSING_KEY)],
    )


def test_passes_the_deacon_context_setting_to_deacon_as_the_data_context_attribute(settings, rf):
    settings.DEACON_KEY = "pk_test123"
    settings.DEACON_CONTEXT = {"site": "docs", "version": "3.2", "beta": True}

    assert render_widget(rf.get("/")) == (
        '<script src="https://heydeacon.com/widget/v1/loader.js" data-key="pk_test123" '
        'data-context="{&quot;site&quot;:&quot;docs&quot;,&quot;version&quot;:&quot;3.2&quot;,'
        '&quot;beta&quot;:true}" async></script>'
    )


def test_keeps_a_context_value_that_looks_like_html_as_it_was_written(settings, rf):
    settings.DEACON_KEY = "pk_test123"
    settings.DEACON_CONTEXT = {"note": '</script><b>"hi" &amp;</b>'}

    assert script_attributes(render_widget(rf.get("/")))["data-context"] == (
        '{"note":"</script><b>\\"hi\\" &amp;</b>"}'
    )


@pytest.mark.parametrize(
    "deacon_context",
    [
        pytest.param("plan=pro", id="a string"),
        pytest.param(["docs"], id="a list"),
        pytest.param({"plan": {"tier": "pro"}}, id="a dict with a nested value"),
        pytest.param({"plan": None}, id="a dict with a None value"),
    ],
)
def test_refuses_a_context_of_the_wrong_type(settings, rf, deacon_context):
    settings.DEACON_KEY = "pk_test123"
    settings.DEACON_CONTEXT = deacon_context

    with pytest.raises(ImproperlyConfigured) as refused:
        render_widget(rf.get("/"))

    assert str(refused.value) == (
        "django-deacon: the DEACON_CONTEXT setting must be a dict whose values are strings, "
        "numbers or booleans."
    )


def test_holds_back_page_views_with_the_data_no_page_views_attribute(settings, rf):
    settings.DEACON_KEY = "pk_test123"
    settings.DEACON_PAGE_VIEWS = False

    assert render_widget(rf.get("/")) == (
        '<script src="https://heydeacon.com/widget/v1/loader.js" data-key="pk_test123" '
        "data-no-page-views async></script>"
    )


def test_refuses_a_page_views_setting_that_is_not_true_or_false(settings, rf):
    settings.DEACON_KEY = "pk_test123"
    settings.DEACON_PAGE_VIEWS = "false"

    with pytest.raises(ImproperlyConfigured) as refused:
        render_widget(rf.get("/"))

    assert str(refused.value) == "django-deacon: the DEACON_PAGE_VIEWS setting must be True or False."
