import re

import pytest
from django.template import Context, Template
from django.test import Client


@pytest.fixture
def browser():
    """A browser on the site, whose POSTs need the CSRF token, as a real one's do."""
    return Client(enforce_csrf_checks=True)


@pytest.fixture
def ana(django_user_model):
    return django_user_model.objects.create_user(
        username="ana", email="ana@studio.com", first_name="Ana", last_name="Ruiz"
    )


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
        '.then((r) => (r.status === 200 ? r.text() : "")) }; '
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
