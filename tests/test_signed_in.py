import json
import logging
import re
from html.parser import HTMLParser

import pytest
from csp.constants import NONCE, SELF
from csp.middleware import CSPMiddleware
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.template import Context, RequestContext, Template
from django.template.context_processors import request as request_processor


def without_csrf_token(html):
    """The page with its CSRF token, which Django masks afresh on every render, swapped for CSRF."""
    return re.sub(r'("X-CSRFTOKEN": ")[^"]+(")', r"\1CSRF\2", html)


@pytest.mark.django_db
def test_tells_deacon_who_is_signed_in_with_a_token_function_above_the_loader_tag(
    settings, browser, ana
):
    settings.DEACON_KEY = "pk_test123"
    browser.force_login(ana)

    assert without_csrf_token(browser.get("/account").content.decode()) == (
        f'<script>window.deaconUser = {{ id: "{ana.pk}", email: "ana@studio.com", '
        'name: "Ana Ruiz", token: (nonce) => fetch("/deacon/token", { method: "POST", '
        'credentials: "same-origin", headers: { "Content-Type": "application/json", '
        '"X-CSRFTOKEN": "CSRF" }, body: JSON.stringify({ nonce }) })'
        '.then((r) => { if (r.status === 204) return ""; '
        'if (!r.ok) throw new Error("Deacon token route answered " + r.status); '
        "return r.text(); }) }; "
        "window.Deacon?.identify(window.deaconUser);</script>"
        '<script src="https://heydeacon.com/widget/v1/loader.js" data-key="pk_test123" async>'
        "</script>"
    )


@pytest.mark.django_db
def test_signs_the_visitor_out_of_deacon_when_nobody_is_signed_in(settings, browser):
    settings.DEACON_KEY = "pk_test123"

    assert browser.get("/account").content.decode() == (
        "<script>window.deaconUser = null; window.Deacon?.identify(null);</script>"
        '<script src="https://heydeacon.com/widget/v1/loader.js" data-key="pk_test123" async>'
        "</script>"
    )


def test_says_nothing_about_who_is_signed_in_when_the_request_has_no_user(settings, rf):
    settings.DEACON_KEY = "pk_test123"
    template = Template("{% load deacon %}{% deacon_widget %}")

    assert template.render(Context({"request": rf.get("/")})) == (
        '<script src="https://heydeacon.com/widget/v1/loader.js" data-key="pk_test123" async>'
        "</script>"
    )


@pytest.mark.parametrize(
    "signed_in", [pytest.param(True, id="someone"), pytest.param(False, id="nobody")]
)
@pytest.mark.django_db
def test_says_nothing_about_who_is_signed_in_when_deacon_signed_in_is_false(
    settings, browser, ana, signed_in
):
    settings.DEACON_KEY = "pk_test123"
    settings.DEACON_SIGNED_IN = False
    if signed_in:
        browser.force_login(ana)

    assert browser.get("/account").content.decode() == (
        '<script src="https://heydeacon.com/widget/v1/loader.js" data-key="pk_test123" async>'
        "</script>"
    )


@pytest.mark.django_db
def test_refuses_a_deacon_signed_in_setting_that_is_not_true_or_false(settings, browser):
    settings.DEACON_KEY = "pk_test123"
    settings.DEACON_SIGNED_IN = "false"

    with pytest.raises(ImproperlyConfigured) as refused:
        browser.get("/account")

    assert (
        str(refused.value) == "django-deacon: the DEACON_SIGNED_IN setting must be True or False."
    )


MISSING_URLS = (
    "django-deacon: the token route isn't in your URLs, so Deacon can't verify who is signed "
    'in. Add path("", include("django_deacon.urls")) to urlpatterns in your urls.py.'
)


@pytest.mark.django_db
def test_names_the_user_without_a_token_and_logs_a_warning_when_the_urls_are_not_included(
    settings, browser, ana, caplog
):
    settings.DEACON_KEY = "pk_test123"
    settings.ROOT_URLCONF = "tests.urls_without_deacon"
    browser.force_login(ana)

    with caplog.at_level(logging.WARNING, logger="django_deacon"):
        page = browser.get("/account").content.decode()

    named = (
        f'<script>window.deaconUser = {{ id: "{ana.pk}", email: "ana@studio.com", '
        'name: "Ana Ruiz" }; window.Deacon?.identify(window.deaconUser);</script>'
        '<script src="https://heydeacon.com/widget/v1/loader.js" data-key="pk_test123" async>'
        "</script>"
    )

    assert (page, caplog.record_tuples) == (
        named,
        [("django_deacon", logging.WARNING, MISSING_URLS)],
    )


class ScriptText(HTMLParser):
    """The text of the first script in some HTML, as a browser reads it."""

    def __init__(self):
        super().__init__()
        self.text = None
        self.reading = False

    def handle_starttag(self, tag, attrs):
        if tag == "script" and self.text is None:
            self.text, self.reading = "", True

    def handle_endtag(self, tag):
        if tag == "script":
            self.reading = False

    def handle_data(self, data):
        if self.reading:
            self.text += data


@pytest.mark.django_db
def test_keeps_a_name_that_looks_like_html_inside_the_script_as_it_was_written(
    settings, browser, django_user_model
):
    settings.DEACON_KEY = "pk_test123"
    dee = django_user_model.objects.create_user(
        username="dee", first_name='</script><b>"hi"', last_name="&amp;</b>"
    )
    browser.force_login(dee)

    parser = ScriptText()
    parser.feed(browser.get("/account").content.decode())
    name = re.search(r'name: ("(?:[^"\\]|\\.)*")', parser.text)

    assert (
        name and json.loads(name.group(1)),
        parser.text.endswith("window.Deacon?.identify(window.deaconUser);"),
    ) == ('</script><b>"hi" &amp;</b>', True)


def test_carries_the_nonce_from_django_csp_on_the_signed_in_script_too(settings, rf):
    settings.DEACON_KEY = "pk_test123"
    settings.CONTENT_SECURITY_POLICY = {"DIRECTIVES": {"script-src": [SELF, NONCE]}}

    def view(request):
        request.user = AnonymousUser()
        template = Template("{% load deacon %}{% deacon_widget %}")
        return HttpResponse(
            template.render(RequestContext(request, processors=[request_processor]))
        )

    response = CSPMiddleware(view)(rf.get("/"))
    nonce = re.search(r"'nonce-([^']+)'", response["Content-Security-Policy"]).group(1)

    assert response.content.decode() == (
        f'<script nonce="{nonce}">window.deaconUser = null; window.Deacon?.identify(null);'
        '</script><script src="https://heydeacon.com/widget/v1/loader.js" data-key="pk_test123" '
        f'async nonce="{nonce}"></script>'
    )
