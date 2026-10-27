from django.urls import path

from tests.urls import account

# A site that has the tag but hasn't included django_deacon.urls.
urlpatterns = [path("account", account)]
