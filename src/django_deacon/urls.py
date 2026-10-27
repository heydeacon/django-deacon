from django.urls import path

from django_deacon import views

app_name = "django_deacon"

urlpatterns = [
    path("deacon/token", views.token, name="token"),
]
