from django.urls import path

from reportes import views


app_name = "reportes"

urlpatterns = [
    path("", views.inicio, name="inicio"),
]
