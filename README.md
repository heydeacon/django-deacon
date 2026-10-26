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

## Options

| Setting             | Type    | Default  | What it does |
| ------------------- | ------- | -------- | ------------ |
| `DEACON_KEY`        | str     | required | Your Deacon key. |
| `DEACON_CONTEXT`    | dict    | none     | Details Deacon takes into account when it answers, the same on every page, such as `{"product": "api", "docs_version": "3.2"}`. Up to 12 keys, each value a string, number or boolean. Anyone can read them in the page's HTML, so never put a secret here. |
| `DEACON_PAGE_VIEWS` | bool    | `True`   | The same script counts visits for Deacon's website analytics. Set this to `False` to send no page views or JavaScript errors from your site. Chat still works. |

```python
DEACON_KEY = "pk_your_widget_key"
DEACON_CONTEXT = {"product": "api", "docs_version": "3.2"}
DEACON_PAGE_VIEWS = False
```

## Content Security Policy

If your site sends a Content Security Policy with a nonce, the tag carries the request's nonce, so `script-src` doesn't need Deacon's address. It reads the nonce from Django's own CSP support (Django 6.0 and later), which needs the `django.template.context_processors.csp` context processor, or from [django-csp](https://pypi.org/project/django-csp/)'s `request.csp_nonce`, which needs `django.template.context_processors.request`.

The chat still needs `https://heydeacon.com` in `connect-src` and `frame-src`, and `'unsafe-inline'` in `style-src`, because the widget writes its styles where a nonce can't reach. Keep the nonce out of `style-src`, since a nonce there makes browsers ignore `'unsafe-inline'`:

```python
from django.utils.csp import CSP

SECURE_CSP = {
    "default-src": [CSP.SELF],
    "script-src": [CSP.SELF, CSP.NONCE],
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

It loads in the background without holding up the page. Works with Django 5.2 and later, on Python 3.11 and later.

## License

MIT
