import pytest
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
