import json
import logging
import re
from types import SimpleNamespace

import jwt
import pytest

from django_deacon import views

SECRET = "deacon_identity_UpMp160sf5EZppi3gLssUsQCcbKrAxq3EdekLOyZ9OU1QX5bY"

# A widget session's nonce, as Deacon makes them: an HMAC-SHA256 in hex.
NONCE = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"

# What the page's token function posts.
BODY = json.dumps({"nonce": NONCE})


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
    browser, ana, monkeypatch
):
    # The view's clock, stopped at 12:00 UTC on 27 October 2026.
    monkeypatch.setattr(views, "time", SimpleNamespace(time=lambda: 1_793_102_400))
    browser.force_login(ana)

    response = ask_for_token(browser)

    token = response.content.decode()
    # That moment has passed, so exp is checked against the value below rather than the clock.
    claims = jwt.decode(token, SECRET, algorithms=["HS256"], options={"verify_exp": False})

    assert (
        response.status_code,
        response["Content-Type"],
        jwt.get_unverified_header(token)["alg"],
        claims,
    ) == (
        200,
        "text/plain; charset=utf-8",
        "HS256",
        {
            "sub": str(ana.pk),
            "email": "ana@studio.com",
            "name": "Ana Ruiz",
            "nonce": NONCE,
            "iat": 1_793_102_400,
            "exp": 1_793_103_000,
        },
    )


@pytest.mark.django_db
def test_answers_204_with_no_token_when_nobody_is_signed_in(browser, ana, settings):
    browser.force_login(ana)
    csrf = csrf_token_on(browser)
    del browser.cookies[settings.SESSION_COOKIE_NAME]  # signed out since the page loaded

    response = post_token(browser, csrf)

    assert (response.status_code, response.content) == (204, b"")


MISSING_SECRET = (
    "django-deacon: DEACON_SECRET is missing, so the token route signs nobody and Deacon can't "
    "verify who is signed in. In Deacon, open Install (the button at the top of the dashboard) "
    "and make a secret under Verify who's signed in. It starts with deacon_identity_."
)


@pytest.mark.parametrize(
    "secret",
    [
        pytest.param(None, id="unset"),
        pytest.param("", id="empty"),
        pytest.param("   ", id="blank"),
    ],
)
@pytest.mark.django_db
def test_answers_204_and_logs_a_warning_when_deacon_secret_is_missing(
    browser, ana, monkeypatch, caplog, secret
):
    if secret is None:
        monkeypatch.delenv("DEACON_SECRET")
    else:
        monkeypatch.setenv("DEACON_SECRET", secret)
    browser.force_login(ana)

    with caplog.at_level(logging.WARNING, logger="django_deacon"):
        response = ask_for_token(browser)

    assert (response.status_code, response.content, caplog.record_tuples) == (
        204,
        b"",
        [("django_deacon", logging.WARNING, MISSING_SECRET)],
    )


@pytest.mark.parametrize(
    ("signed_in", "status"),
    [pytest.param(True, 200, id="a token"), pytest.param(False, 204, id="no token")],
)
@pytest.mark.django_db
def test_tells_caches_never_to_keep_its_answer(browser, ana, settings, signed_in, status):
    browser.force_login(ana)
    csrf = csrf_token_on(browser)
    if not signed_in:
        del browser.cookies[settings.SESSION_COOKIE_NAME]

    response = post_token(browser, csrf)

    assert (response.status_code, response.headers.get("Cache-Control")) == (
        status,
        "no-store, private",
    )


@pytest.mark.django_db
def test_sends_no_cors_headers_so_only_the_sites_own_pages_can_read_a_token(browser, ana):
    browser.force_login(ana)

    response = ask_for_token(browser)

    cors = [name for name in response.headers if name.lower().startswith("access-control-")]
    assert (response.status_code, cors) == (200, [])


@pytest.mark.django_db
def test_refuses_a_request_without_the_pages_csrf_token_as_the_site_refuses_any_post(browser, ana):
    browser.force_login(ana)
    browser.get("/account")

    response = browser.post("/deacon/token", BODY, content_type="application/json")

    assert response.status_code == 403


@pytest.mark.parametrize(
    "body",
    [
        pytest.param("{}", id="missing"),
        pytest.param(json.dumps({"nonce": 42}), id="not a string"),
        pytest.param(json.dumps({"nonce": "a" * 129}), id="longer than 128 characters"),
        pytest.param(json.dumps({"nonce": "abc def"}), id="more than letters, digits, - and _"),
        pytest.param("nonce=abc", id="in a body that isn't JSON"),
        pytest.param(json.dumps([NONCE]), id="in JSON that isn't an object"),
    ],
)
@pytest.mark.django_db
def test_answers_400_with_no_token_when_the_nonce_is_wrong(browser, ana, body):
    browser.force_login(ana)

    response = ask_for_token(browser, body)

    assert (response.status_code, response.content) == (400, b"")


@pytest.mark.django_db
def test_signs_only_the_details_the_user_has(browser, django_user_model):
    bo = django_user_model.objects.create_user(username="bo")
    browser.force_login(bo)

    response = ask_for_token(browser)

    claims = jwt.decode(response.content, SECRET, algorithms=["HS256"])
    assert {name: claims[name] for name in claims if name not in ("iat", "exp")} == {
        "sub": str(bo.pk),
        "nonce": NONCE,
    }
