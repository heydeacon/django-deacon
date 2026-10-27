import json
import logging
import os
import time
from functools import wraps

import jwt
from django.http import HttpResponse
from django.views.decorators.http import require_POST

from django_deacon import users

logger = logging.getLogger("django_deacon")

# How long a token lasts. Deacon refuses one that lasts more than 15 minutes.
LIFETIME = 10 * 60

MISSING_SECRET = (
    "django-deacon: DEACON_SECRET is missing, so the token route signs nobody and Deacon can't "
    "verify who is signed in. In Deacon, open Install (the button at the top of the dashboard) "
    "and make a secret under Verify who's signed in. It starts with dk_sec_."
)


def _never_stored(view):
    """
    A token names one person, so no cache in front of the site may keep one for another: every
    answer the view gives says so.
    """

    @wraps(view)
    def answer(request, *args, **kwargs):
        response = view(request, *args, **kwargs)
        response["Cache-Control"] = "no-store, private"
        return response

    return answer


@_never_stored
@require_POST
def token(request):
    """
    POST /deacon/token, which the page's token function calls when the chat opens: a token
    saying who is signed in, signed with DEACON_SECRET, for Deacon to check. It sits behind the
    site's CSRF protection, as every other POST on the site does.
    """
    nonce = json.loads(request.body)["nonce"]

    # AnonymousUser when nobody is signed in, which names nobody.
    if not request.user.is_authenticated:
        return HttpResponse(status=204)

    # The key is the whole secret as Deacon showed it, dk_sec_ and all.
    secret = os.environ.get("DEACON_SECRET", "").strip()

    if secret == "":
        logger.warning(MISSING_SECRET)
        return HttpResponse(status=204)

    user = users.details(request.user)
    now = int(time.time())
    claims = {
        "sub": user["id"],
        "email": user["email"],
        "name": user["name"],
        "nonce": nonce,
        "iat": now,
        "exp": now + LIFETIME,
    }

    signed = jwt.encode(claims, secret, algorithm="HS256")

    return HttpResponse(signed, content_type="text/plain; charset=utf-8")
