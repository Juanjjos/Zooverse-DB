from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from reportes.alertas import obtener_alertas
from reportes.consultas import construir_datos_reportes
from reportes.forms import FiltroReportesForm


def pagina_inicio(request):
    return render(request, "reportes/portada.html")


def _requiere_administrador(user):
    return (
        user.is_superuser
        or user.groups.filter(name="Administrador").exists()
    )


@login_required(login_url="/admin/login/")
def inicio(request):
    if not _requiere_administrador(request.user):
        raise PermissionDenied

    formulario = FiltroReportesForm(request.GET if request.GET else {})
    datos_reportes = {}
    if formulario.is_valid():
        filtros = formulario.cleaned_data
        datos_reportes = construir_datos_reportes(
            fecha_inicio=filtros["fecha_inicio"],
            fecha_fin=filtros["fecha_fin"],
            especie_id=filtros["especie"].pk if filtros["especie"] else None,
        )

    return render(
        request,
        "reportes/inicio.html",
        {
            "formulario": formulario,
            "datos_reportes": datos_reportes,
        },
    )


@login_required(login_url="/admin/login/")
def panel_alertas(request):
    if not _requiere_administrador(request.user):
        raise PermissionDenied

    return render(
        request,
        "reportes/alertas.html",
        {"alertas": obtener_alertas()},
    )
