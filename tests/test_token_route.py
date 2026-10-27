import json
import re
import time

import jwt
import pytest
from django.test import Client

SECRET = "dk_sec_Wf3pX9qLr2Tz8vNc4bJh6yKd1sMa7eGu0oPiQwErTyU"

# A widget session's nonce, as Deacon makes them: an HMAC-SHA256 in hex.
NONCE = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"

# What the page's token function posts.
BODY = json.dumps({"nonce": NONCE})


@pytest.fixture
def browser():
    """A browser on the site, whose POSTs need the CSRF token, as a real one's do."""
    return Client(enforce_csrf_checks=True)


@pytest.fixture
def ana(django_user_model):
    return django_user_model.objects.create_user(
        username="ana", email="ana@studio.com", first_name="Ana", last_name="Ruiz"
    )


@pytest.fixture(autouse=True)
def deacon(settings, monkeypatch):
    settings.DEACON_KEY = "pk_test123"
    monkeypatch.setenv("DEACON_SECRET", SECRET)


def csrf_token_on(browser):
    """The CSRF token the signed-in script on a page of the site sends."""
    page = browser.get("/account").content.decode()
    return re.search(r'"X-CSRFTOKEN": "([^"]+)"', page).group(1)


def post_token(browser, csrf, body=BODY):
    """What the page's token function sends: the JSON body, with the CSRF token it printed."""
    return browser.post(
        "/deacon/token", body, content_type="application/json", headers={"X-CSRFToken": csrf}
    )


def ask_for_token(browser, body=BODY):
    return post_token(browser, csrf_token_on(browser), body)


@pytest.mark.django_db
def test_answers_with_a_token_deacon_accepts_hs256_with_deacon_secret_naming_who_is_signed_in(
    browser, ana
):
    browser.force_login(ana)

    before = int(time.time())
    response = ask_for_token(browser)
    after = int(time.time())

    token = response.content.decode()
    claims = jwt.decode(token, SECRET, algorithms=["HS256"])
    iat = claims.pop("iat")
    exp = claims.pop("exp")

    assert (
        response.status_code,
        response["Content-Type"],
        jwt.get_unverified_header(token)["alg"],
        claims,
        before <= iat <= after,
        exp - iat,
    ) == (
        200,
        "text/plain; charset=utf-8",
        "HS256",
        {"sub": str(ana.pk), "email": "ana@studio.com", "name": "Ana Ruiz", "nonce": NONCE},
        True,
        600,
    )


@pytest.mark.django_db
def test_answers_204_with_no_token_when_nobody_is_signed_in(browser, ana, settings):
    browser.force_login(ana)
    csrf = csrf_token_on(browser)
    del browser.cookies[settings.SESSION_COOKIE_NAME]  # signed out since the page loaded

    response = post_token(browser, csrf)

    assert (response.status_code, response.content) == (204, b"")
