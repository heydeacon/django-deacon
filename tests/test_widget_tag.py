from django.template import Context, Template


def render_widget(request, **variables):
    """What a base template's {% deacon_widget %} prints for this request."""
    template = Template("{% load deacon %}{% deacon_widget %}")
    return template.render(Context({"request": request, **variables}))


def test_prints_the_tag_from_install_with_the_key_from_the_deacon_key_setting(settings, rf):
    settings.DEACON_KEY = "pk_test123"

    assert render_widget(rf.get("/")) == (
        '<script src="https://heydeacon.com/widget/v1/loader.js" data-key="pk_test123" async>'
        "</script>"
    )
