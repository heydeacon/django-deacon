# django-deacon

[Deacon](https://heydeacon.com) is an AI support agent that answers questions from your own docs and content, and says when it doesn't know. This app adds its chat widget to every page of a Django site.

You need a Deacon account, and there's a free plan.

## Install

```sh
pip install django-deacon
```

## Set it up

Add the app and your key to `settings.py`:

```python
INSTALLED_APPS = [
    # ...the rest of your apps
    "django_deacon",
]

DEACON_KEY = "pk_your_widget_key"
```

Then load the tag in the `<head>` of your base template:

```django
{% load deacon %}
<head>
  {# ...the rest of your head #}
  {% deacon_widget %}
</head>
```

To find your key, open Install from the button at the top of the Deacon dashboard. The snippet there has it in `data-key`, and it starts with `pk_`. It isn't a secret, since every visitor's browser reads it, but you can read it from the environment like any setting: `DEACON_KEY = os.environ.get("DEACON_KEY")`. If the key is missing, the tag prints nothing and logs a warning that says why, so your pages still render. A setting of the wrong type raises `ImproperlyConfigured`, which says why.

Deacon only runs on the sites listed on Install. A listed domain covers its subdomains, so `example.com` covers `app.example.com`. If your site lives somewhere else, such as `example.fly.dev`, add that address on Install too.

When you run `python manage.py runserver`, Install notices the widget on `127.0.0.1:8000` and lets you add it in one click. Chats on a development address don't count towards your plan.

## Who is signed in

When someone is signed in to your site, the tag tells Deacon their id, email and name, so their conversations show who they are. To have Deacon trust that, rather than take the page's word for it, add the app's URLs to your `urls.py`:

```python
from django.urls import include, path

urlpatterns = [
    # ...the rest of your URLs
    path("", include("django_deacon.urls")),
]
```

Then give it your secret in the `DEACON_SECRET` environment variable:

```sh
DEACON_SECRET=deacon_identity_your_secret
```

To make one, open Install in Deacon and use Make a secret under Verify who's signed in. You see it once. The key the app signs with is the whole string exactly as Install shows it, `deacon_identity_` and all, not decoded or shortened. Keep it on the server: unlike the `pk_` key, anyone who has it can tell Deacon they are any of your users.

With both in place, the app does the rest:

- Above the widget's tag it prints `window.deaconUser`, with the user's id, email and name and a `token` function.
- When the chat opens, `token` posts to `/deacon/token`, the view the URLs add. It answers with a token signed with `DEACON_SECRET` that names the user and this chat and lasts 10 minutes. With nobody signed in, or no secret, it answers 204 and signs nothing. Its answers are never cached and carry no CORS headers, so only your own pages can read them.
- On a page where nobody is signed in, it prints `window.deaconUser = null` and `Deacon.identify(null)` instead, so signing out ends what Deacon knew about the last person, and the next person on that computer starts fresh.

The user is `request.user`, from Django's `AuthenticationMiddleware`, and the tag finds the request in the template's context, as it is when a view renders with `render()`. Anyone whose `is_authenticated` is false counts as nobody. The id is the user's primary key, so it must name one person across your whole site. The email is the user model's email field, and the name is `get_full_name()`, when the user has them. Without the URLs, the tag still names the user, with no `token` function, and logs a warning that says what to add.

If your base template sets `window.deaconUser` itself, from an earlier version of Deacon's install guide, take that script out: the tag prints it now.

### CSRF

The view sits behind Django's CSRF protection, as every other POST on your site does, and the `token` function sends the CSRF token in the header Django checks. The view changes nothing, and with no CORS headers another site couldn't read its answer, so `csrf_exempt` would be safe too. Keeping the check means a page on another site can't get your server to sign anything at all, and nothing in your site is exempt from it.

### Staging and development

Give staging its own Deacon team, with its own key and secret, or leave `DEACON_SECRET` unset there so the view answers 204. Never copy production's secret to staging or a laptop: whoever runs that server could sign a token for any of your users.

### Signing in in the browser

If your site learns who is signed in in the browser, such as a React front end on a token-authenticated API, `request.user` is nobody on every page, and the sign-out line would start everyone afresh on every page load. Turn it off, and tell Deacon from your own code with `Deacon.identify`, as [Deacon's install guide](https://heydeacon.com/agent/install.md) shows:

```python
DEACON_SIGNED_IN = False
```

## Options

| Setting             | Type    | Default  | What it does |
| ------------------- | ------- | -------- | ------------ |
| `DEACON_KEY`        | str     | none     | Your Deacon key. Without it the tag prints nothing and logs a warning. |
| `DEACON_CONTEXT`    | dict    | none     | Details Deacon takes into account when it answers, the same on every page, such as `{"product": "api", "docs_version": "3.2"}`. Up to 12 keys, each value a string, number or boolean. Anyone can read them in the page's HTML, so never put a secret here. |
| `DEACON_PAGE_VIEWS` | bool    | `True`   | The same script counts visits for Deacon's website analytics. Set this to `False` to send no page views or JavaScript errors from your site. Chat still works. |
| `DEACON_SIGNED_IN`  | bool    | `True`   | Tell Deacon who is signed in, and sign them out of Deacon on pages where nobody is. Set this to `False` if your site signs people in in the browser. |

```python
DEACON_KEY = "pk_your_widget_key"
DEACON_CONTEXT = {"product": "api", "docs_version": "3.2"}
DEACON_PAGE_VIEWS = False
```

The secret isn't a setting, only the `DEACON_SECRET` environment variable, so it stays out of your code.

## Content Security Policy

If your site sends a Content Security Policy with a nonce, the tag carries the request's nonce, on the signed-in script too. It reads it from Django's own CSP support (Django 6.0 and later), which needs the `django.template.context_processors.csp` context processor, or from [django-csp](https://pypi.org/project/django-csp/)'s `request.csp_nonce`, which needs `django.template.context_processors.request`.

The policy also needs Deacon's address, `https://heydeacon.com`, in `script-src`, `connect-src` and `frame-src`, and `'unsafe-inline'` in `style-src`, because the widget writes its styles where a nonce can't reach. Keep the nonce out of `style-src`, since a nonce there makes browsers ignore `'unsafe-inline'`:

```python
from django.utils.csp import CSP

SECURE_CSP = {
    "default-src": [CSP.SELF],
    "script-src": [CSP.SELF, CSP.NONCE, "https://heydeacon.com"],
    "style-src": [CSP.SELF, CSP.UNSAFE_INLINE],
    "connect-src": [CSP.SELF, "https://heydeacon.com"],
    "frame-src": ["https://heydeacon.com"],
}
```

## Opening the chat from your own button

The widget comes with its own button. To use one of yours instead, hide Deacon's in Appearance in the dashboard and call `window.Deacon.open()` from your button or link. `Deacon.close()` and `Deacon.toggle()` work too.

## What it adds

The tag prints the same tag Install gives you:

```html
<script src="https://heydeacon.com/widget/v1/loader.js" data-key="pk_your_widget_key" async></script>
```

It loads in the background without holding up the page. Above it, when someone is signed in, goes the signed-in script, here spread over lines:

```html
<script>
  window.deaconUser = {
    id: "7",
    email: "ana@studio.com",
    name: "Ana Ruiz",
    token: (nonce) => fetch("/deacon/token", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFTOKEN": "…" },
      body: JSON.stringify({ nonce }),
    }).then((r) => (r.status === 200 ? r.text() : "")),
  };
  window.Deacon?.identify(window.deaconUser);
</script>
```

Works with Django 5.2 and later, on Python 3.11 and later.

## License

MIT
