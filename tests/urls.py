from django.http import HttpResponse
from django.template import RequestContext, Template
from django.urls import include, path


def account(request):
    """A page of the site, whose base template has the tag in its head."""
    template = Template("{% load deacon %}{% deacon_widget %}")
    return HttpResponse(template.render(RequestContext(request)))


urlpatterns = [
    path("account", account),
    path("", include("django_deacon.urls")),
]
