import json
import os
import time

import jwt
from django.http import HttpResponse
from django.views.decorators.http import require_POST

from django_deacon import users

# How long a token lasts. Deacon refuses one that lasts more than 15 minutes.
LIFETIME = 10 * 60


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

    # The key is the whole secret as Deacon showed it, dk_sec_ and all.
    signed = jwt.encode(claims, os.environ["DEACON_SECRET"], algorithm="HS256")

    return HttpResponse(signed, content_type="text/plain; charset=utf-8")
